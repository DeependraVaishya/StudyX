const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");


// ================================
// REGISTER
// ================================

if (registerForm) {

    registerForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        const name = document
            .getElementById("registerName")
            .value
            .trim();

        const email = document
            .getElementById("registerEmail")
            .value
            .trim()
            .toLowerCase();

        const password = document
            .getElementById("registerPassword")
            .value;

        const confirmPassword = document
            .getElementById("confirmPassword")
            .value;


        if (password !== confirmPassword) {
            alert("Passwords do not match.");
            return;
        }


        if (password.length < 6) {
            alert("Password must be at least 6 characters.");
            return;
        }


        try {

            const response = await fetch(
                "http://127.0.0.1:8000/register",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        name: name,
                        email: email,
                        password: password
                    })
                }
            );


            const data = await response.json();


            if (!response.ok) {
                alert(data.detail || "Registration failed.");
                return;
            }


            alert(data.message);

            registerForm.reset();


        } catch (error) {

            console.error(error);

            alert(
                "Cannot connect to StudyX server. " +
                "Please make sure FastAPI is running."
            );
        }
    });
}


// ================================
// LOGIN
// ================================

if (loginForm) {

    loginForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        const email = document
            .getElementById("loginEmail")
            .value
            .trim()
            .toLowerCase();

        const password = document
            .getElementById("loginPassword")
            .value;


        if (!email || !password) {
            alert("Please enter email and password.");
            return;
        }


        try {

            const response = await fetch(
                "http://127.0.0.1:8000/login",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        email: email,
                        password: password
                    })
                }
            );


            const data = await response.json();


            if (!response.ok) {
                alert(data.detail || "Login failed.");
                return;
            }


            alert(
                `Welcome back, ${data.name}!`
            );


            // Save logged-in user
            localStorage.setItem(
                "studyxUser",
                JSON.stringify(data)
            );


            // Go to StudyX home
            window.location.href = "index.html";


        } catch (error) {

            console.error(error);

            alert(
                "Cannot connect to StudyX server. " +
                "Please make sure FastAPI is running."
            );
        }
    });
}