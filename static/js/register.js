const registerForm = document.getElementById("registerForm");
const passwordInput = document.getElementById("password");
const confirmPasswordInput = document.getElementById("confirm_password");

if (registerForm) {
    registerForm.addEventListener("submit", function (event) {
        const password = passwordInput.value.trim();
        const confirmPassword = confirmPasswordInput.value.trim();

        if (password !== confirmPassword) {
            event.preventDefault();
            alert("Passwords do not match.");
        }
    });
}
