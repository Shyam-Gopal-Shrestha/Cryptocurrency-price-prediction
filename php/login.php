<?php
session_start();

ini_set('display_errors', '1');
ini_set('display_startup_errors', '1');
error_reporting(E_ALL);

header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode([
        'ok' => false,
        'error' => 'Method not allowed'
    ]);
    exit;
}

$host = 'localhost';
$dbname = 'ansush_crypto_prediction';
$dbuser = 'root';
$dbpass = '';

try {
    $pdo = new PDO(
        "mysql:host=$host;dbname=$dbname;charset=utf8mb4",
        $dbuser,
        $dbpass,
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
        ]
    );
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'ok' => false,
        'error' => 'Database connection failed: ' . $e->getMessage()
    ]);
    exit;
}

$rawInput = file_get_contents('php://input');
$input = json_decode($rawInput, true);

if (!is_array($input)) {
    $input = $_POST;
}

$email = isset($input['email']) ? strtolower(trim($input['email'])) : '';
$password = isset($input['password']) ? (string)$input['password'] : '';

if ($email === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(422);
    echo json_encode([
        'ok' => false,
        'error' => 'Invalid email address'
    ]);
    exit;
}

if ($password === '') {
    http_response_code(422);
    echo json_encode([
        'ok' => false,
        'error' => 'Password is required'
    ]);
    exit;
}

$stmt = $pdo->prepare("
    SELECT id, username, email, password_hash, first_name, last_name, role, status
    FROM users
    WHERE email = ?
    LIMIT 1
");
$stmt->execute([$email]);
$user = $stmt->fetch();

if (!$user) {
    http_response_code(401);
    echo json_encode([
        'ok' => false,
        'error' => 'Email not found'
    ]);
    exit;
}

if ($user['status'] !== 'active') {
    http_response_code(403);
    echo json_encode([
        'ok' => false,
        'error' => 'Your account is not active'
    ]);
    exit;
}

if (!password_verify($password, $user['password_hash'])) {
    http_response_code(401);
    echo json_encode([
        'ok' => false,
        'error' => 'Incorrect password'
    ]);
    exit;
}

$updateLogin = $pdo->prepare("UPDATE users SET last_login = NOW() WHERE id = ?");
$updateLogin->execute([$user['id']]);

$_SESSION['user_id'] = $user['id'];
$_SESSION['username'] = $user['username'];
$_SESSION['email'] = $user['email'];
$_SESSION['role'] = $user['role'];
$_SESSION['first_name'] = $user['first_name'];
$_SESSION['last_name'] = $user['last_name'];

echo json_encode([
    'ok' => true,
    'message' => 'Login successful',
    'role' => $user['role'],
    'username' => $user['username']
]);