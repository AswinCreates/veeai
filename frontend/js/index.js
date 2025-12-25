async function generateText() {
    const prompt = document.getElementById("prompt").value;
    const token = localStorage.getItem("access_token");

    const res = await fetch("http://127.0.0.1:8000/generate-text", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        },
        body: JSON.stringify({ prompt })
    });

    const data = await res.json();

    if (res.ok) {
        document.getElementById("output").innerText = data.response;
    } else {
        alert("Session expired, please login again");
        logout();
    }
}
