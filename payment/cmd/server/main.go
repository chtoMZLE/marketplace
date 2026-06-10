package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/marketplace/payment/internal/db"
	"github.com/marketplace/payment/internal/escrow"
	"github.com/marketplace/payment/internal/handlers"
)

func main() {
	ctx := context.Background()

	dsn := os.Getenv("PAYMENT_DB_DSN")
	if dsn == "" {
		log.Fatal("PAYMENT_DB_DSN is required")
	}

	var pool interface{ Close() }
	for i := range 10 {
		p, err := db.Connect(ctx, dsn)
		if err == nil {
			if err := db.InitSchema(ctx, p); err != nil {
				log.Fatalf("init schema: %v", err)
			}
			escrow.Global = escrow.NewStore(p)
			pool = p
			break
		}
		log.Printf("db connect attempt %d: %v — retrying in 2s", i+1, err)
		time.Sleep(2 * time.Second)
	}
	if pool == nil {
		log.Fatal("could not connect to postgres after 10 attempts")
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", healthHandler)
	handlers.RegisterEscrowRoutes(mux)
	handlers.RegisterChainRoutes(mux)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8001"
	}

	log.Printf("payment service listening on :%s", port)
	if err := http.ListenAndServe(":"+port, corsMiddleware(mux)); err != nil {
		log.Fatal(err)
	}
}

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func healthHandler(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}
