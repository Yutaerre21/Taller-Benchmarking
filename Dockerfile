FROM golang:1.24-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go test ./... && CGO_ENABLED=0 go build -trimpath -o /orders .

FROM alpine:3.22
RUN adduser -D -u 10001 app
COPY --from=build /orders /usr/local/bin/orders
USER app
EXPOSE 5001
CMD ["orders"]
