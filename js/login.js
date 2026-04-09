document.addEventListener("DOMContentLoaded", () => {
  console.log("login.js loaded");

  const form = document.getElementById("loginForm");
  const feedback = document.getElementById("feedback");
  const togglePassword = document.querySelector(".toggle-password");

  function showMessage(message, type = "error") {
    if (!feedback) return alert(message);
    feedback.textContent = message;
    feedback.className = `feedback ${type}`;
    feedback.style.display = "block";
  }

  function clearMessage() {
    if (!feedback) return;
    feedback.textContent = "";
    feedback.className = "feedback";
    feedback.style.display = "none";
  }

  if (togglePassword) {
    togglePassword.addEventListener("click", () => {
      const passwordInput = document.getElementById("password");
      if (!passwordInput) return;

      if (passwordInput.type === "password") {
        passwordInput.type = "text";
        togglePassword.classList.remove("fa-eye");
        togglePassword.classList.add("fa-eye-slash");
      } else {
        passwordInput.type = "password";
        togglePassword.classList.remove("fa-eye-slash");
        togglePassword.classList.add("fa-eye");
      }
    });
  }

  if (!form) {
    console.error("Login form not found");
    return;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearMessage();

    const email = document.getElementById("email")?.value.trim().toLowerCase() || "";
    const password = document.getElementById("password")?.value || "";

    if (!email || !password) {
      return showMessage("Please enter both email and password.");
    }

    if (!/^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/.test(email)) {
      return showMessage("Please enter a valid email address.");
    }

    try {
      const response = await fetch("../php/login.php", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ email, password })
      });

      const text = await response.text();
      console.log("server response:", text);

      let data;
      try {
        data = JSON.parse(text);
      } catch {
        return showMessage("Invalid server response.");
      }

      if (!response.ok || !data.ok) {
        return showMessage(data.error || "Login failed.");
      }

      showMessage("Login successful. Redirecting...", "success");

      setTimeout(() => {
        switch (data.role) {
          case "admin":
            window.location.href = "admin-redirect.html";
            break;
          case "researcher":
            window.location.href = "researcher-redirect.html";
            break;
          default:
            window.location.href = "user-redirect.html";
            break;
        }
      }, 1200);
    } catch (error) {
      console.error("fetch error:", error);
      showMessage("Network error. Please try again.");
    }
  });
});