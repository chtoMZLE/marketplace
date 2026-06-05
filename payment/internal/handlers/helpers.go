package handlers

import (
	"encoding/json"
	"net/http"
)

func respond(w http.ResponseWriter, data any, status int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

func httpError(w http.ResponseWriter, msg string, status int) {
	respond(w, map[string]string{"error": msg}, status)
}
