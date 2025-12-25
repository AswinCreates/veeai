async function loginUser() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    const res = await fetch("http://127.0.0.1:8000/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    if (res.ok) {
        localStorage.setItem("access_token", data.access_token);
        window.location.href = "chat.html";
    } else {
        alert(data.detail);
    }
}
