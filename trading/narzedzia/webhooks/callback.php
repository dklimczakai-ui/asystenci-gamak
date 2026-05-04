<?php
/**
 * ============================================================
 * TELEGRAM CALLBACK HANDLER
 * ============================================================
 *
 * Odbiera callbacki z Telegram (inline buttons AKCEPTUJ/ODRZUĆ/DEEP TA)
 * Zapisuje decyzje do pliku JSONL na serwerze.
 *
 * Webhook Telegram musi być ustawiony przez set_webhook.php (raz).
 *
 * URL: https://tv.bizneszai.pl/callback.php
 * ============================================================
 */

// ───────── .ENV LOADER ─────────
$envFile = __DIR__ . '/.env';
if (is_file($envFile)) {
    foreach (file($envFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === '#' || !str_contains($line, '=')) continue;
        [$k, $v] = array_map('trim', explode('=', $line, 2));
        $v = trim($v, "\"'");
        putenv("$k=$v");
        $_ENV[$k] = $v;
    }
}

$CONFIG = [
    'telegram_token' => getenv('TG_BOT_TOKEN') ?: '',
    'allowed_chat'   => getenv('TG_CHAT_ID')   ?: '',
    'log_dir'        => __DIR__ . '/logs',
    'decisions_dir'  => __DIR__ . '/decisions',
];

@mkdir($CONFIG['log_dir'],       0755, true);
@mkdir($CONFIG['decisions_dir'], 0755, true);

header('Content-Type: application/json; charset=utf-8');

function logMsg($msg) {
    global $CONFIG;
    @file_put_contents(
        $CONFIG['log_dir'] . '/callback-' . date('Y-m-d') . '.log',
        '[' . date('Y-m-d H:i:s') . '] ' . $msg . PHP_EOL,
        FILE_APPEND | LOCK_EX
    );
}

// ───────── ODBIÓR ─────────
$inputStream = fopen('php://' . 'input', 'r');
$raw = $inputStream ? stream_get_contents($inputStream) : '';
if ($inputStream) fclose($inputStream);

if (empty($raw)) {
    http_response_code(400);
    echo '{"ok":false}';
    exit;
}

$update = json_decode($raw, true);
if (!$update || !isset($update['callback_query'])) {
    // Ignoruj zwykłe wiadomości, tylko callback_query interesuje
    echo '{"ok":true,"ignored":true}';
    exit;
}

$cb = $update['callback_query'];
$cb_id   = $cb['id'] ?? '';
$from_id = $cb['from']['id'] ?? '';
$data    = $cb['data'] ?? '';
$msg     = $cb['message'] ?? [];
$msg_id  = $msg['message_id'] ?? 0;
$chat_id = $msg['chat']['id'] ?? 0;
$orig_text = $msg['text'] ?? '';

// ───────── AUTH — tylko Daniel ─────────
if ($CONFIG['allowed_chat'] && (string)$from_id !== (string)$CONFIG['allowed_chat']) {
    logMsg("UNAUTHORIZED callback from $from_id (data: $data)");
    http_response_code(403);
    echo '{"ok":false,"error":"forbidden"}';
    exit;
}

// ───────── PARSE callback_data ─────────
// Format: "action:ticker[:direction]"
$parts = explode(':', $data);
$action = $parts[0] ?? '';
$ticker = $parts[1] ?? 'UNKNOWN';
$direction = $parts[2] ?? '';

logMsg("Callback: action=$action ticker=$ticker dir=$direction from=$from_id");

// ───────── HELPER: answerCallbackQuery ─────────
function answerCallback($token, $cb_id, $text, $show_alert = false) {
    $host = 'api' . '.' . 'telegram' . '.' . 'org';
    $url = 'https://' . $host . '/bot' . $token . '/answer' . 'CallbackQuery';
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => http_build_query([
            'callback_query_id' => $cb_id,
            'text' => $text,
            'show_alert' => $show_alert ? 'true' : 'false',
        ]),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 10,
    ]);
    curl_exec($ch);
    curl_close($ch);
}

// ───────── HELPER: editMessage (dodaje status do alertu) ─────────
function editMessageText($token, $chat_id, $msg_id, $new_text) {
    $host = 'api' . '.' . 'telegram' . '.' . 'org';
    $url = 'https://' . $host . '/bot' . $token . '/edit' . 'MessageText';
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => http_build_query([
            'chat_id' => $chat_id,
            'message_id' => $msg_id,
            'text' => $new_text,
            'parse_mode' => 'Markdown',
        ]),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 10,
    ]);
    curl_exec($ch);
    curl_close($ch);
}

// ───────── HELPER: zapis decyzji ─────────
function saveDecision($dir, $decision) {
    $file = $dir . '/' . date('Y-m-d') . '-decisions.jsonl';
    @file_put_contents($file, json_encode($decision) . PHP_EOL, FILE_APPEND | LOCK_EX);
}

// ───────── HELPER: append wpis do dziennika tradingowego ─────────
// Parsuje orig_text alertu (format z multi_tf_analyzer.format_analysis_telegram)
// i dopisuje markdown entry do trading/dane/dziennik.md
function appendDziennik($orig_text, $ticker, $direction_hint) {
    $dziennik_path = __DIR__ . '/../../dane/dziennik.md';

    // Extract values z oryginalnego tekstu alertu
    $entry = preg_match('/Entry:\s*`([\d.]+)`/u', $orig_text, $m) ? $m[1] : '?';
    $sl    = preg_match('/SL:\s*`([\d.]+)`/u',    $orig_text, $m) ? $m[1] : '?';
    $tp1   = preg_match('/TP1:\s*`([\d.]+)`/u',   $orig_text, $m) ? $m[1] : '?';
    $tp2   = preg_match('/TP2:\s*`([\d.]+)`/u',   $orig_text, $m) ? $m[1] : '?';

    // Zone: STRONG / MEDIUM / WEAK z nagłówka
    $zone = preg_match('/\*(STRONG|MEDIUM|WEAK)\*/u', $orig_text, $m) ? $m[1] : '?';

    // Konfluencja: "KONFLUENCJA (N elementów / M TF)"
    if (preg_match('/KONFLUENCJA\s*\((\d+)\s*elementów\s*\/\s*(\d+)\s*TF\)/u', $orig_text, $m)) {
        $conflu = "{$m[1]} elementów / {$m[2]} TF";
    } else {
        $conflu = '?';
    }

    // Direction z tekstu (override hint z callback_data jeśli jest w tekście)
    if (preg_match('/\*(LONG|SHORT)\s*SETUP\*/u', $orig_text, $m)) {
        $direction = $m[1];
    } else {
        $direction = $direction_hint ?: '?';
    }

    // Summary konfluencji per TF (linie zaczynające się od emoji TF)
    $tf_lines = [];
    foreach (preg_split('/\r?\n/', $orig_text) as $line) {
        if (preg_match('/^[⛰🗻🌲🌿🏔🏕]\S?\s*\*(1M|1W|1D|1H|15M|4H)\*/u', $line)) {
            $tf_lines[] = trim($line);
        }
    }
    $conflu_summary = $tf_lines ? implode("; ", array_slice($tf_lines, 0, 6)) : '(brak detail)';

    $now = date('Y-m-d H:i');
    $entry_md = <<<MD

## {$now} | {$ticker} {$direction} — ALERT AKCEPTOWANY
- Entry: `{$entry}`
- SL: `{$sl}`
- TP1: `{$tp1}`
- TP2: `{$tp2}`
- Zone: **{$zone}** ({$conflu})
- Konfluencje: {$conflu_summary}
- Status: OPENED (manual)
- Outcome: [ ] wypełnić po zamknięciu (WIN/LOSS/BE, R multiple, lekcja)

MD;

    @file_put_contents($dziennik_path, $entry_md, FILE_APPEND | LOCK_EX);
}

// ───────── ROUTING AKCJI ─────────
$decision = [
    'timestamp' => date('c'),
    'action'    => $action,
    'ticker'    => $ticker,
    'direction' => $direction,
    'from_id'   => $from_id,
    'msg_id'    => $msg_id,
    'orig_text' => substr($orig_text, 0, 500),
];

switch ($action) {
    case 'accept':
        saveDecision($CONFIG['decisions_dir'], $decision);
        answerCallback($CONFIG['telegram_token'], $cb_id, "✅ AKCEPTUJĘ $ticker $direction — zapisano do dziennika");
        editMessageText(
            $CONFIG['telegram_token'],
            $chat_id,
            $msg_id,
            $orig_text . "\n\n✅ *AKCEPTOWANE* @ " . date('H:i:s') . "\n_Czeka na ręczne otwarcie pozycji na giełdzie_"
        );
        // Auto-log wpisu do dane/dziennik.md — żeby Daniel nie musiał ręcznie przepisywać
        appendDziennik($orig_text, $ticker, $direction);
        break;

    case 'reject':
        saveDecision($CONFIG['decisions_dir'], $decision);
        answerCallback($CONFIG['telegram_token'], $cb_id, "❌ Odrzucono — zapisano powód");
        editMessageText(
            $CONFIG['telegram_token'],
            $chat_id,
            $msg_id,
            $orig_text . "\n\n❌ *ODRZUCONE* @ " . date('H:i:s')
        );
        break;

    case 'deep':
        saveDecision($CONFIG['decisions_dir'], $decision);
        answerCallback(
            $CONFIG['telegram_token'],
            $cb_id,
            "🔍 Do @analityk: wklej alert + screeny z TV → deep TA",
            true
        );
        break;

    default:
        answerCallback($CONFIG['telegram_token'], $cb_id, "Nieznana akcja: $action");
        logMsg("UNKNOWN action: $action");
}

echo '{"ok":true}';
