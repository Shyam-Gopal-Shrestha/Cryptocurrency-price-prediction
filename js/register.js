document.addEventListener("DOMContentLoaded", () => {
  console.log("register.js loaded");

  const form = document.getElementById("registerForm");
  const feedback = document.getElementById("feedback");
  const toggleIcons = document.querySelectorAll(".toggle-password");

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

  toggleIcons.forEach((icon) => {
    icon.addEventListener("click", () => {
      const input = icon.parentElement.querySelector("input");
      if (!input) return;

      if (input.type === "password") {
        input.type = "text";
        icon.classList.remove("fa-eye");
        icon.classList.add("fa-eye-slash");
      } else {
        input.type = "password";
        icon.classList.remove("fa-eye-slash");
        icon.classList.add("fa-eye");
      }
    });
  });

  if (!form) {
    console.error("Form not found");
    return;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    console.log("form submitted");
    clearMessage();

    const fullname = document.getElementById("fullname")?.value.trim() || "";
    const email = document.getElementById("email")?.value.trim().toLowerCase() || "";
    const role = document.getElementById("role")?.value.trim().toLowerCase() || "user";
    const password = document.getElementById("password")?.value || "";
    const confirmPassword = document.getElementById("confirmPassword")?.value || "";

    if (!fullname || !email || !password || !confirmPassword) {
      return showMessage("Please complete all required fields.");
    }

    if (!/^[A-Za-z' -]{2,}$/.test(fullname)) {
      return showMessage("Please enter a valid full name.");
    }

    if (!/^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$/.test(email)) {
      return showMessage("Please enter a valid email address.");
    }

    if (password !== confirmPassword) {
      return showMessage("Passwords do not match.");
    }

    if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&]).{8,72}$/.test(password)) {
      return showMessage("Password must include uppercase, lowercase, number, and special character.");
    }

    try {
      const response = await fetch("../php/register.php", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          fullname,
          email,
          password,
          confirmPassword,
          role
        })
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
        return showMessage(data.error || "Registration failed.");
      }

      showMessage("Registration successful. Redirecting to login page...", "success");

      setTimeout(() => {
        window.location.href = "login.html";
      }, 1500);
    } catch (error) {
      console.error("fetch error:", error);
      showMessage("Network error. Please try again.");
    }
  });
});