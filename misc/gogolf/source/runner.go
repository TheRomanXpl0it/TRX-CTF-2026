package main

import (
	"time"
	"bufio"
	"context"
	"strings"
	"encoding/base64"
	"io"
	"os"
	"os/exec"
	"os/signal"
	"syscall"

)

func die(s string) int {
	os.Stderr.WriteString(s + "\n")
	return 1
}

func main() {
	os.Exit(run())
}

func run() int {
	os.Stdout.WriteString("> lemme see your <=72 bytes gogolf source code (b64):\n")
	os.Stdout.WriteString(strings.Repeat("v", 53) + "\n")

	line, err := bufio.NewReader(os.Stdin).ReadString('\n')
	if err != nil && err != io.EOF {
		return die("read error")
	}
	src, err := base64.StdEncoding.DecodeString(line)
	if err != nil {
		return die("decode error")
	}

	if len(src) == 0 {
		return 0
	}
	if len(src) > 72 {
		os.Stdout.WriteString("too long\n")
		return 1
	}

	dir, err := os.MkdirTemp("", "gogolf-")
	if err != nil {
		return die("tmpdir error")
	}
	defer os.RemoveAll(dir)

	path := dir + "/main.go"
	if err := os.WriteFile(path, src, 0o600); err != nil {
		return die("write error")
	}

	ctx, stop := context.WithTimeout(context.Background(), 5*time.Second)
	defer stop()

	cmd := exec.CommandContext(ctx, "/usr/local/go/bin/go", "run", path)
	cmd.Stdout, cmd.Stderr = os.Stdout, os.Stderr

	signal.Ignore(syscall.SIGHUP, syscall.SIGINT, syscall.SIGPIPE, syscall.SIGTERM)
	defer signal.Reset(syscall.SIGHUP, syscall.SIGINT, syscall.SIGPIPE, syscall.SIGTERM)

	if err := cmd.Run(); err != nil {
		if ctx.Err() != nil {
			return die("timeout")
		}
		if e, ok := err.(*exec.ExitError); ok {
			return e.ExitCode()
		}
		return die("exec error")
	}

	return 0
}
