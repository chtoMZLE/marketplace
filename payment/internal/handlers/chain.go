package handlers

import (
	"math/rand"
	"net/http"
	"os"

	"github.com/marketplace/payment/internal/chain"
	"github.com/marketplace/payment/internal/escrow"
)

func RegisterChainRoutes(mux *http.ServeMux) {
	mux.HandleFunc("GET /chain", chainHandler)
	mux.HandleFunc("GET /chain/verify", chainVerifyHandler)

	// Demo-only: only registered when DEMO_MODE=true
	if os.Getenv("DEMO_MODE") == "true" {
		mux.HandleFunc("POST /chain/tamper", chainTamperHandler)
	}
}

func chainHandler(w http.ResponseWriter, _ *http.Request) {
	txs := escrow.Global.Chain().All()
	if txs == nil {
		txs = []*chain.Transaction{}
	}
	respond(w, txs, http.StatusOK)
}

func chainTamperHandler(w http.ResponseWriter, _ *http.Request) {
	txs := escrow.Global.Chain().All()
	if len(txs) == 0 {
		httpError(w, "цепочка пуста — сначала создайте заказ", http.StatusBadRequest)
		return
	}
	idx := rand.Intn(len(txs)) // #nosec G404 — demo tamper, non-cryptographic randomness is intentional
	id, ok := escrow.Global.TamperChain(idx)
	if !ok {
		httpError(w, "не удалось изменить запись", http.StatusInternalServerError)
		return
	}
	respond(w, map[string]any{"tampered_index": idx + 1, "tampered_id": id}, http.StatusOK)
}

func chainVerifyHandler(w http.ResponseWriter, _ *http.Request) {
	broken := escrow.Global.Chain().Verify()
	if len(broken) == 0 {
		respond(w, map[string]any{"valid": true}, http.StatusOK)
		return
	}
	respond(w, map[string]any{"valid": false, "broken": broken}, http.StatusOK)
}
