package main

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha1"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// CloudConfig 云端（腾讯云COS）配置。
// 与数据一起存放在 %APPDATA%\PomodoroTimer\ 目录，软件目录不产生文件。
type CloudConfig struct {
	Endpoint  string `json:"endpoint"`
	Region    string `json:"region"`
	Bucket    string `json:"bucket"`
	AccessKey string `json:"access_key"`
	SecretKey string `json:"secret_key"`
	Prefix    string `json:"prefix"`
	ObjectKey string `json:"object_key"`
	Enabled   bool   `json:"enabled"`
}

// DefaultCloudConfig 返回内置的默认云端配置。
func DefaultCloudConfig() CloudConfig {
	return CloudConfig{
		Endpoint:  "https://cos.ap-guangzhou.myqcloud.com",
		Region:    "ap-guangzhou",
		Bucket:    "",
		AccessKey: "",
		SecretKey: "",
		Prefix:    "backups/",
		ObjectKey: "pomodoro_data.json",
		Enabled:   false,
	}
}

// CloudClient 封装对象存储操作。
type CloudClient struct {
	cfg CloudConfig
}

// LoadCloudConfig 从数据目录读取云端配置，不存在时返回默认配置。
func LoadCloudConfig(dir string) CloudConfig {
	cfg := DefaultCloudConfig()
	raw, err := os.ReadFile(filepath.Join(dir, "cloud.json"))
	if err != nil {
		return cfg
	}
	_ = json.Unmarshal(raw, &cfg)
	return cfg
}

// SaveCloudConfig 把云端配置写回数据目录。
func SaveCloudConfig(dir string, cfg CloudConfig) error {
	body, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(dir, "cloud.json"), body, 0o644)
}

// NewCloudClient 根据配置创建客户端。
func NewCloudClient(cfg CloudConfig) (*CloudClient, error) {
	if cfg.Bucket == "" {
		return nil, fmt.Errorf("请先填写 Bucket")
	}
	return &CloudClient{cfg: cfg}, nil
}

// objectKey 返回完整对象名（前缀 + 对象名）。
func (c *CloudClient) objectKey() string {
	prefix := c.cfg.Prefix
	if prefix != "" && !strings.HasSuffix(prefix, "/") {
		prefix += "/"
	}
	key := c.cfg.ObjectKey
	if key == "" {
		key = "pomodoro_data.json"
	}
	return prefix + key
}

// virtualHostURL 构建腾讯云COS virtual-hosted style URL
// endpoint: cos.ap-guangzhou.myqcloud.com
// bucket: 
// 结果: https://.cos.ap-guangzhou.myqcloud.com/key
func (c *CloudClient) virtualHostURL(key string) string {
	endpoint := c.cfg.Endpoint
	if !strings.HasPrefix(endpoint, "http") {
		endpoint = "https://" + endpoint
	}
	endpoint = strings.TrimSuffix(endpoint, "/")
	schemeIdx := strings.Index(endpoint, "://")
	scheme := endpoint[:schemeIdx]
	host := endpoint[schemeIdx+3:]
	return fmt.Sprintf("%s://%s.%s/%s", scheme, c.cfg.Bucket, host, key)
}

// cosSign 计算腾讯云COS签名（HMAC-SHA1方案）
// 返回 Authorization 头值
func (c *CloudClient) cosSign(method, uriPath, queryString string, headers map[string]string) string {
	// 1. KeyTime = StartTimestamp;EndTimestamp
	now := time.Now().Unix()
	expire := now + 600 // 10分钟有效
	keyTime := fmt.Sprintf("%d;%d", now, expire)

	// 2. SignKey = HMAC-SHA1(SecretKey, KeyTime) → hex
	signKey := hmacSHA1Hex(c.cfg.SecretKey, keyTime)

	// 3. 构建 HeaderList 和 HttpHeaders
	// 必须包含 host
	headerKeys := make([]string, 0, len(headers))
	for k := range headers {
		headerKeys = append(headerKeys, k)
	}
	// 按 key 排序
	for i := 0; i < len(headerKeys); i++ {
		for j := i + 1; j < len(headerKeys); j++ {
			if headerKeys[i] > headerKeys[j] {
				headerKeys[i], headerKeys[j] = headerKeys[j], headerKeys[i]
			}
		}
	}

	headerList := strings.Join(headerKeys, ";")
	httpHeadersParts := make([]string, 0, len(headerKeys))
	for _, k := range headerKeys {
		httpHeadersParts = append(httpHeadersParts, k+"="+cosURLEncode(headers[k]))
	}
	httpHeaders := strings.Join(httpHeadersParts, "&")

	// 4. 构建 UrlParamList 和 HttpParameters（从 queryString）
	urlParamList := ""
	httpParameters := ""
	if queryString != "" {
		params := strings.Split(queryString, "&")
		paramMap := make(map[string]string)
		paramKeys := make([]string, 0)
		for _, p := range params {
			kv := strings.SplitN(p, "=", 2)
			k := cosURLEncode(strings.ToLower(kv[0]))
			v := ""
			if len(kv) > 1 {
				v = kv[1]
			}
			paramMap[k] = v
			paramKeys = append(paramKeys, k)
		}
		// 排序
		for i := 0; i < len(paramKeys); i++ {
			for j := i + 1; j < len(paramKeys); j++ {
				if paramKeys[i] > paramKeys[j] {
					paramKeys[i], paramKeys[j] = paramKeys[j], paramKeys[i]
				}
			}
		}
		paramParts := make([]string, 0, len(paramKeys))
		for _, k := range paramKeys {
			paramParts = append(paramParts, k+"="+paramMap[k])
		}
		urlParamList = strings.Join(paramKeys, ";")
		httpParameters = strings.Join(paramParts, "&")
	}

	// 5. HttpString = method\nuriPath\nhttpParameters\nhttpHeaders\n
	httpString := fmt.Sprintf("%s\n%s\n%s\n%s\n",
		strings.ToLower(method), uriPath, httpParameters, httpHeaders)

	// 6. StringToSign = sha1\nKeyTime\nSHA1(HttpString)\n
	sha1HttpString := sha1Hex(httpString)
	stringToSign := fmt.Sprintf("sha1\n%s\n%s\n", keyTime, sha1HttpString)

	// 7. Signature = HMAC-SHA1(SignKey, StringToSign) → hex
	signature := hmacSHA1Hex(signKey, stringToSign)

	// 8. Authorization
	auth := fmt.Sprintf("q-sign-algorithm=sha1&q-ak=%s&q-sign-time=%s&q-key-time=%s&q-header-list=%s&q-url-param-list=%s&q-signature=%s",
		c.cfg.AccessKey, keyTime, keyTime, headerList, urlParamList, signature)

	return auth
}

// hmacSHA1Hex 用 HMAC-SHA1 计算摘要，返回16进制小写字符串
func hmacSHA1Hex(key, data string) string {
	mac := hmac.New(sha1.New, []byte(key))
	mac.Write([]byte(data))
	return hex.EncodeToString(mac.Sum(nil))
}

// sha1Hex 计算SHA1摘要，返回16进制小写字符串
func sha1Hex(data string) string {
	h := sha1.Sum([]byte(data))
	return hex.EncodeToString(h[:])
}

// cosURLEncode 对COS签名中的value进行URL编码
func cosURLEncode(s string) string {
	// COS要求对特殊字符编码
	u := url.QueryEscape(s)
	// url.QueryEscape 会把空格变成 +，但COS要求变成 %20
	u = strings.ReplaceAll(u, "+", "%20")
	return u
}

// Test 通过列举对象验证连接与权限。
func (c *CloudClient) Test(ctx context.Context) error {
	urlStr := fmt.Sprintf("%s?max-keys=1", c.virtualHostURL(""))

	req, err := http.NewRequestWithContext(ctx, "GET", urlStr, nil)
	if err != nil {
		return err
	}

	host := req.URL.Host
	headers := map[string]string{
		"host": host,
	}
	auth := c.cosSign("GET", "/", "max-keys=1", headers)
	req.Header.Set("Authorization", auth)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)

	if resp.StatusCode != 200 {
		return fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}
	return nil
}

// Upload 上传整份数据。
func (c *CloudClient) Upload(ctx context.Context, body []byte) error {
	key := c.objectKey()
	urlStr := c.virtualHostURL(key)

	req, err := http.NewRequestWithContext(ctx, "PUT", urlStr, bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Content-Length", fmt.Sprintf("%d", len(body)))

	host := req.URL.Host
	headers := map[string]string{
		"host":           host,
		"content-type":   "application/json",
		"content-length": fmt.Sprintf("%d", len(body)),
	}
	auth := c.cosSign("PUT", "/"+key, "", headers)
	req.Header.Set("Authorization", auth)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		rbody, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("上传失败 HTTP %d: %s", resp.StatusCode, string(rbody))
	}
	return nil
}

// Download 下载整份数据；对象不存在时返回 nil, nil。
func (c *CloudClient) Download(ctx context.Context) ([]byte, error) {
	key := c.objectKey()
	urlStr := c.virtualHostURL(key)

	req, err := http.NewRequestWithContext(ctx, "GET", urlStr, nil)
	if err != nil {
		return nil, err
	}

	host := req.URL.Host
	headers := map[string]string{
		"host": host,
	}
	auth := c.cosSign("GET", "/"+key, "", headers)
	req.Header.Set("Authorization", auth)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode == 404 {
		return nil, nil // 对象不存在
	}
	if resp.StatusCode != 200 {
		rbody, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("下载失败 HTTP %d: %s", resp.StatusCode, string(rbody))
	}
	return io.ReadAll(resp.Body)
}

// cloudTimeout 为云端操作设置统一超时。
func cloudTimeout() (context.Context, context.CancelFunc) {
	return context.WithTimeout(context.Background(), 20*time.Second)
}
