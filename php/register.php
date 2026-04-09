<?php
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
$dbpass = '';   // XAMPP default is usually empty

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

$fullname = isset($input['fullname']) ? trim($input['fullname']) : '';
$email = isset($input['email']) ? strtolower(trim($input['email'])) : '';
$pass = isset($input['password']) ? (string)$input['password'] : '';
$pass2 = isset($input['confirmPassword']) ? (string)$input['confirmPassword'] : '';
$role = isset($input['role']) ? strtolower(trim((string)$input['role'])) : 'user';

$allowedRoles = ['user', 'admin', 'researcher'];
if (!in_array($role, $allowedRoles, true)) {
    $role = 'user';
}

if ($fullname === '' || !preg_match("/^[A-Za-z' -]{2,}$/u", $fullname)) {
    http_response_code(422);
    echo json_encode(['ok' => false, 'error' => 'Invalid full name']);
    exit;
}

if ($email === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(422);
    echo json_encode(['ok' => false, 'error' => 'Invalid email address']);
    exit;
}

if (!preg_match('/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&]).{8,72}$/', $pass)) {
    http_response_code(422);
    echo json_encode(['ok' => false, 'error' => 'Weak password']);
    exit;
}

if ($pass !== $pass2) {
    http_response_code(422);
    echo json_encode(['ok' => false, 'error' => 'Passwords do not match']);
    exit;
}

$checkEmail = $pdo->prepare("SELECT 1 FROM users WHERE email = ? LIMIT 1");
$checkEmail->execute([$email]);

if ($checkEmail->fetch()) {
    http_response_code(409);
    echo json_encode(['ok' => false, 'error' => 'Email already registered']);
    exit;
}

$nameParts = preg_split('/\s+/', $fullname);
$firstName = $nameParts[0] ?? '';
$lastName = count($nameParts) > 1 ? implode(' ', array_slice($nameParts, 1)) : '';

$baseUsername = preg_replace('/[^A-Za-z0-9_]/', '_', explode('@', $email)[0]);
if ($baseUsername === '') {
    $baseUsername = 'user';
}
$baseUsername = substr($baseUsername, 0, 30);
$generatedUsername = $baseUsername;

$checkUsername = $pdo->prepare("SELECT 1 FROM users WHERE username = ? LIMIT 1");
$counter = 0;

while (true) {
    $checkUsername->execute([$generatedUsername]);
    if (!$checkUsername->fetch()) {
        break;
    }
    $counter++;
    $generatedUsername = substr($baseUsername, 0, 28) . $counter;
}

$passwordHash = password_hash($pass, PASSWORD_DEFAULT);

$insert = $pdo->prepare("
    INSERT INTO users (username, email, password_hash, first_name, last_name, role)
    VALUES (?, ?, ?, ?, ?, ?)
");

$insert->execute([
    $generatedUsername,
    $email,
    $passwordHash,
    $firstName,
    $lastName,
    $role
]);

echo json_encode([
    'ok' => true,
    'message' => 'Registration successful',
    'username' => $generatedUsername,
    'role' => $role
]);