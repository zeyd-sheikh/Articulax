const loginForm = document.getElementById("loginForm");
const loginPassword = document.getElementById("login_password");

if (loginForm) {
    loginForm.addEventListener("submit", function (event) {
        if (loginPassword.value.trim() === "") {
            event.preventDefault();
            alert("Password is required.");
        }
    });
}