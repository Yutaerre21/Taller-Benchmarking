package main

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math/big"
	"net/http"
	"net/url"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"
	"unicode/utf8"

	"github.com/jackc/pgx/v5/pgxpool"
)

type Item struct {
	ProductID string      `json:"productId"`
	Quantity  int64       `json:"quantity"`
	Price     json.Number `json:"price"`
}
type Order struct {
	CustomerID string `json:"customerId"`
	Items      []Item `json:"items"`
}

// PostgreSQL NUMERIC(10,2) admite como máximo 99 999 999.99.
const maxCents int64 = 9999999999

func cents(n json.Number) (int64, error) {
	r, ok := new(big.Rat).SetString(n.String())
	if !ok || r.Sign() < 0 {
		return 0, fmt.Errorf("price debe ser un número no negativo")
	}
	r.Mul(r, big.NewRat(100, 1))
	if !r.IsInt() || !r.Num().IsInt64() || r.Num().Int64() > maxCents {
		return 0, fmt.Errorf("price debe tener máximo dos decimales y caber en NUMERIC(10,2)")
	}
	return r.Num().Int64(), nil
}
func money(c int64) string  { return fmt.Sprintf("%d.%02d", c/100, c%100) }
func validID(s string) bool { return strings.TrimSpace(s) != "" && utf8.RuneCountInString(s) <= 50 }
func totals(o Order) (int64, int64, error) {
	if !validID(o.CustomerID) || len(o.Items) == 0 || len(o.Items) > 1000 {
		return 0, 0, fmt.Errorf("customerId es obligatorio (máximo 50 caracteres); items debe contener de 1 a 1000 elementos")
	}
	var total, count int64
	for _, item := range o.Items {
		p, err := cents(item.Price)
		if err != nil {
			return 0, 0, err
		}
		if !validID(item.ProductID) || item.Quantity <= 0 || item.Quantity > 2147483647-count {
			return 0, 0, fmt.Errorf("productId inválido o quantity fuera de rango")
		}
		if p > 0 && item.Quantity > (maxCents-total)/p {
			return 0, 0, fmt.Errorf("totalAmount excede NUMERIC(10,2)")
		}
		total += p * item.Quantity
		count += item.Quantity
	}
	return total, count, nil
}
func respond(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(data)
}
func fail(w http.ResponseWriter, status int, message string) {
	respond(w, status, map[string]string{"error": message})
}

func handler(pool *pgxpool.Pool) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
		defer cancel()
		if err := pool.Ping(ctx); err != nil {
			fail(w, 503, "base de datos no disponible")
			return
		}
		respond(w, 200, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /api/orders", func(w http.ResponseWriter, r *http.Request) {
		r.Body = http.MaxBytesReader(w, r.Body, 1024*1024)
		dec := json.NewDecoder(r.Body)
		dec.DisallowUnknownFields()
		var order Order
		if err := dec.Decode(&order); err != nil {
			fail(w, 400, "JSON inválido")
			return
		}
		if err := dec.Decode(new(any)); err != io.EOF {
			fail(w, 400, "se requiere un único objeto JSON")
			return
		}
		total, count, err := totals(order)
		if err != nil {
			fail(w, 400, err.Error())
			return
		}
		var random [16]byte
		if _, err := rand.Read(random[:]); err != nil {
			fail(w, 500, "no se pudo generar el identificador")
			return
		}
		id := hex.EncodeToString(random[:])
		ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
		defer cancel()
		tx, err := pool.Begin(ctx)
		if err != nil {
			fail(w, 503, "base de datos no disponible")
			return
		}
		defer func() {
			cleanup, cancel := context.WithTimeout(context.Background(), 2*time.Second)
			defer cancel()
			_ = tx.Rollback(cleanup)
		}()
		var created time.Time
		err = tx.QueryRow(ctx, `INSERT INTO orders(order_id,customer_id,total_amount,items_count) VALUES($1,$2,$3,$4) RETURNING created_at`, id, order.CustomerID, money(total), count).Scan(&created)
		if err == nil {
			for _, item := range order.Items {
				p, _ := cents(item.Price)
				_, err = tx.Exec(ctx, `INSERT INTO order_items(order_id,product_id,quantity,price) VALUES($1,$2,$3,$4)`, id, item.ProductID, item.Quantity, money(p))
				if err != nil {
					break
				}
			}
		}
		if err == nil {
			err = tx.Commit(ctx)
		}
		if err != nil {
			log.Printf("guardar pedido: %v", err)
			fail(w, 500, "no se pudo guardar el pedido")
			return
		}
		respond(w, 201, map[string]any{"orderId": id, "totalAmount": json.Number(money(total)), "itemsCount": count, "processedAt": created.UTC().Format(time.RFC3339Nano)})
	})
	return mux
}
func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	u := &url.URL{Scheme: "postgres", User: url.UserPassword(env("DB_USER", "postgres"), env("DB_PASSWORD", "postgres")), Host: env("DB_HOST", "localhost") + ":" + env("DB_PORT", "5433"), Path: env("DB_NAME", "orders_db"), RawQuery: "sslmode=disable"}
	cfg, err := pgxpool.ParseConfig(u.String())
	if err != nil {
		log.Fatal(err)
	}
	max, err := strconv.ParseInt(env("DB_MAX_CONNS", "20"), 10, 32)
	if err != nil || max < 1 {
		log.Fatal("DB_MAX_CONNS debe ser un entero positivo")
	}
	cfg.MaxConns = int32(max)
	pool, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		log.Fatal(err)
	}
	defer pool.Close()
	ping, cancel := context.WithTimeout(ctx, 10*time.Second)
	err = pool.Ping(ping)
	cancel()
	if err != nil {
		log.Fatal(err)
	}
	server := &http.Server{Addr: ":5001", Handler: handler(pool), ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 15 * time.Second, IdleTimeout: 60 * time.Second}
	go func() {
		<-ctx.Done()
		shutdown, cancel := context.WithTimeout(context.Background(), 15*time.Second)
		defer cancel()
		_ = server.Shutdown(shutdown)
	}()
	log.Print("API Go escuchando en :5001")
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
}
