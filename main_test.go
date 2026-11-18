package main

import (
	"encoding/json"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestTotals(t *testing.T) {
	tests := []struct {
		name, body   string
		total, count int64
		invalid      bool
	}{
		{"ejemplo", `{"customerId":"C123","items":[{"productId":"P1","quantity":2,"price":10.5},{"productId":"P2","quantity":1,"price":5}]}`, 2600, 3, false},
		{"decimal exacto", `{"customerId":"C","items":[{"productId":"P","quantity":3,"price":0.1}]}`, 30, 3, false},
		{"vacío", `{"customerId":"C","items":[]}`, 0, 0, true},
		{"negativo", `{"customerId":"C","items":[{"productId":"P","quantity":-1,"price":5}]}`, 0, 0, true},
		{"desbordamiento", `{"customerId":"C","items":[{"productId":"P","quantity":2,"price":99999999.99}]}`, 0, 0, true},
		{"fracción centavo", `{"customerId":"C","items":[{"productId":"P","quantity":1,"price":0.001}]}`, 0, 0, true},
		{"sin precio", `{"customerId":"C","items":[{"productId":"P","quantity":1}]}`, 0, 0, true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var o Order
			if err := json.Unmarshal([]byte(tt.body), &o); err != nil {
				t.Fatal(err)
			}
			total, count, err := totals(o)
			if (err != nil) != tt.invalid || (!tt.invalid && (total != tt.total || count != tt.count)) {
				t.Fatalf("got %d,%d,%v", total, count, err)
			}
		})
	}
}
func TestRejectMalformedWithoutDB(t *testing.T) {
	for _, body := range []string{`{`, `{} {}`, `{"extra":true}`, `null`} {
		r := httptest.NewRequest("POST", "/api/orders", strings.NewReader(body))
		w := httptest.NewRecorder()
		handler(nil).ServeHTTP(w, r)
		if w.Code != 400 {
			t.Fatalf("%q: status %d", body, w.Code)
		}
	}
}
