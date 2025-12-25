function checkAuth() {
    const token = localStorage.getItem("access_token");

    if (!token) {
        window.location.href = "login.html";
    }
}

function logout() {
    localStorage.removeItem("access_token");
    window.location.href = "login.html";
}
