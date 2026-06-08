package handlers

import (
	"net/http"

	"github.com/marketplace/payment/internal/chain"
	"github.com/marketplace/payment/internal/escrow"
)

func RegisterChainRoutes(mux *http.ServeMux) {
	mux.HandleFunc("GET /chain", chainHandler)
	mux.HandleFunc("GET /chain/verify", chainVerifyHandler)
	mux.HandleFunc("POST /chain/tamper", chainTamperHandler)
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
	// Tamper the middle transaction so the break propagates visibly through the rest.
	idx := len(txs) / 2
	id, ok := escrow.Global.Chain().Tamper(idx)
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
