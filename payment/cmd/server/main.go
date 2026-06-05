package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"

	"github.com/marketplace/payment/internal/handlers"
)

func main() {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /health", healthHandler)

	handlers.RegisterEscrowRoutes(mux)
	handlers.RegisterChainRoutes(mux)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8001"
	}

	log.Printf("payment service listening on :%s", port)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatal(err)
	}
}

func healthHandler(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}
