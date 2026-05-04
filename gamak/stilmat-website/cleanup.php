<?php
// One-shot WordPress cleanup script
// Run once via HTTPS, then delete this file

// Security: only run from localhost or with secret key
$secret = $_GET['key'] ?? '';
if ($secret !== 'stilmat-cleanup-2026-04-09-xkv7') {
    http_response_code(403);
    die('Forbidden');
}

set_time_limit(300);
ini_set('memory_limit', '256M');

$root = __DIR__;
$deleted = ['files' => 0, 'dirs' => 0];
$errors = [];

function rrmdir($dir, &$deleted, &$errors) {
    if (!is_dir($dir)) return;
    $items = @scandir($dir);
    if ($items === false) {
        $errors[] = "scandir failed: $dir";
        return;
    }
    foreach ($items as $item) {
        if ($item === '.' || $item === '..') continue;
        $path = $dir . DIRECTORY_SEPARATOR . $item;
        if (is_dir($path)) {
            rrmdir($path, $deleted, $errors);
        } else {
            if (@unlink($path)) {
                $deleted['files']++;
            } else {
                $errors[] = "unlink failed: $path";
            }
        }
    }
    if (@rmdir($dir)) {
        $deleted['dirs']++;
    } else {
        $errors[] = "rmdir failed: $dir";
    }
}

// === DELETE WORDPRESS DIRECTORIES ===
$dirsToDelete = [
    'wp-admin',
    'wp-includes',
    'wp-content/plugins',
    'wp-content/themes',
    'wp-content/languages',
    'wp-content/upgrade',
    'wp-content/cache',
    'wp-content/mu-plugins',
    'wp-content/uploads',  // we have local copies in images/
    'wp-content',
    'cgi-bin',
];

foreach ($dirsToDelete as $dir) {
    rrmdir($root . '/' . $dir, $deleted, $errors);
}

// === DELETE WORDPRESS FILES ===
$filesToDelete = [
    'wp-activate.php',
    'wp-blog-header.php',
    'wp-comments-post.php',
    'wp-config.php',
    'wp-config-sample.php',
    'wp-cron.php',
    'wp-links-opml.php',
    'wp-load.php',
    'wp-login.php',
    'wp-mail.php',
    'wp-settings.php',
    'wp-signup.php',
    'wp-trackback.php',
    'xmlrpc.php',
    'index.php',
    'license.txt',
    'readme.html',
    '.htaccess.bk',
    '.htaccess.preinstall',
    'index.html.backup.a17082fa4dc818708844407d4b84dfd2',
];

foreach ($filesToDelete as $file) {
    $path = $root . '/' . $file;
    if (file_exists($path)) {
        if (@unlink($path)) {
            $deleted['files']++;
        } else {
            $errors[] = "unlink failed: $file";
        }
    }
}

// === RESULT ===
header('Content-Type: text/plain; charset=utf-8');
echo "=== STILMAT WORDPRESS CLEANUP ===\n\n";
echo "Files deleted: {$deleted['files']}\n";
echo "Directories deleted: {$deleted['dirs']}\n";

if (!empty($errors)) {
    echo "\nERRORS (" . count($errors) . "):\n";
    foreach (array_slice($errors, 0, 30) as $err) {
        echo "  - $err\n";
    }
    if (count($errors) > 30) {
        echo "  ... and " . (count($errors) - 30) . " more\n";
    }
}

echo "\n=== REMAINING FILES IN ROOT ===\n";
$remaining = scandir($root);
foreach ($remaining as $item) {
    if ($item === '.' || $item === '..') continue;
    $path = $root . '/' . $item;
    $type = is_dir($path) ? '[DIR]' : '[FILE]';
    $size = is_file($path) ? ' (' . filesize($path) . 'b)' : '';
    echo "  $type $item$size\n";
}

echo "\nDONE. Now delete this cleanup.php file.\n";
