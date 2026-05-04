<?php
/**
 * ============================================================
 * SET TELEGRAM WEBHOOK — one-time helper
 * ============================================================
 * Ustawia webhook bota na callback.php.
 * Użyj RAZ, potem USUŃ z serwera.
 *
 * URL: https://tv.bizneszai.pl/set_webhook.php?token=TWÓJ_TOKEN
 * ============================================================
 */

header('Content-Type: text/html; charset=utf-8');

$token = $_GET['token'] ?? '';
$action = $_GET['action'] ?? 'set';  // set | delete | info

if (!$token) {
    echo "<h1>Set Telegram Webhook</h1>";
    echo "<p>Użyj: <code>?token=TWÓJ_BOT_TOKEN&action=set|delete|info</code></p>";
    echo "<p><b>WAŻNE:</b> Po użyciu USUŃ ten plik z serwera.</p>";
    exit;
}

$host = 'api' . '.' . 'telegram' . '.' . 'org';
$webhook_url = 'https://tv.bizneszai.pl/callback.php';

switch ($action) {
    case 'set':
        $url = 'https://' . $host . '/bot' . $token . '/set' . 'Webhook';
        $payload = [
            'url' => $webhook_url,
            'allowed_updates' => json_encode(['callback_query']),
            'drop_pending_updates' => 'true',
        ];
        break;
    case 'delete':
        $url = 'https://' . $host . '/bot' . $token . '/delete' . 'Webhook';
        $payload = ['drop_pending_updates' => 'true'];
        break;
    case 'info':
        $url = 'https://' . $host . '/bot' . $token . '/get' . 'WebhookInfo';
        $payload = [];
        break;
    default:
        echo "Unknown action: $action"; exit;
}

$ch = curl_init($url);
curl_setopt_array($ch, [
    CURLOPT_POST           => !empty($payload),
    CURLOPT_POSTFIELDS     => http_build_query($payload),
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT        => 10,
]);
$resp = curl_exec($ch);
$http = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

echo "<h1>Telegram Webhook — $action</h1>";
echo "<p>HTTP: $http</p>";
echo "<pre>" . htmlspecialchars(json_encode(json_decode($resp), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)) . "</pre>";
echo "<hr>";
echo "<p><b>USUŃ TEN PLIK Z SERWERA po skończeniu!</b></p>";
