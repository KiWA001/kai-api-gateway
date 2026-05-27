package claude

import (
	"net/http"
	"strings"

	"github.com/router-for-me/CLIProxyAPI/v7/sdk/config"
	"github.com/router-for-me/CLIProxyAPI/v7/sdk/proxyutil"
	log "github.com/sirupsen/logrus"
)

// NewAnthropicHttpClient creates an HTTP client for Anthropic OAuth calls.
// It keeps configured proxy support while using Go's standard transport.
func NewAnthropicHttpClient(cfg *config.SDKConfig) *http.Client {
	transport := &http.Transport{
		Proxy:             http.ProxyFromEnvironment,
		ForceAttemptHTTP2: true,
	}

	if cfg != nil {
		proxyURL := strings.TrimSpace(cfg.ProxyURL)
		if proxyURL != "" {
			proxyTransport, _, errBuild := proxyutil.BuildHTTPTransport(proxyURL)
			if errBuild != nil {
				log.Errorf("failed to configure proxy transport for %q: %v", proxyutil.Redact(proxyURL), errBuild)
			} else if proxyTransport != nil {
				transport = proxyTransport
			}
		}
	}

	return &http.Client{Transport: transport}
}
