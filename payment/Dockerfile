FROM golang:1.23-alpine AS builder

WORKDIR /app

# Copy all sources first so go mod tidy can resolve imports
COPY . .
RUN go mod tidy && go build -o server ./cmd/server

FROM alpine:3.20

WORKDIR /app

COPY --from=builder /app/server .

EXPOSE 8001

CMD ["./server"]
