const API_URL = "http://127.0.0.1:8000";

const user = JSON.parse(localStorage.getItem("studyxUser"));

if (!user) {
    window.location.href = "login.html";
}


// =====================================================
// ELEMENTS
// =====================================================

const userName = document.getElementById("userName");
const userEmail = document.getElementById("userEmail");
const userAvatar = document.getElementById("userAvatar");

const materialSelect = document.getElementById("materialSelect");
const questionCount = document.getElementById("questionCount");
const difficulty = document.getElementById("difficulty");

const generateQuizBtn =
    document.getElementById("generateQuizBtn");

const quizStatus =
    document.getElementById("quizStatus");

const quizSetup =
    document.getElementById("quizSetup");

const quizLoading =
    document.getElementById("quizLoading");

const quizContainer =
    document.getElementById("quizContainer");

const quizResult =
    document.getElementById("quizResult");

const questionsContainer =
    document.getElementById("questionsContainer");

const submitQuizBtn =
    document.getElementById("submitQuizBtn");

const restartQuizBtn =
    document.getElementById("restartQuizBtn");

const tryAgainBtn =
    document.getElementById("tryAgainBtn");

const quizTitle =
    document.getElementById("quizTitle");

const questionProgress =
    document.getElementById("questionProgress");

const scoreValue =
    document.getElementById("scoreValue");

const percentageValue =
    document.getElementById("percentageValue");

const resultMessage =
    document.getElementById("resultMessage");

const logoutBtn =
    document.getElementById("logoutBtn");


// =====================================================
// USER INFO
// =====================================================

if (user) {

    userName.textContent =
        user.name || "Student";

    userEmail.textContent =
        user.email || "";

    if (user.name) {

        userAvatar.textContent =
            user.name.charAt(0).toUpperCase();

    }
}


// =====================================================
// LOAD STUDY MATERIALS
// =====================================================

async function loadMaterials() {

    try {

        const response = await fetch(
            `${API_URL}/materials?email=${encodeURIComponent(user.email)}`
        );

        if (!response.ok) {
            throw new Error("Failed to load materials");
        }

        const data =
            await response.json();

        const materials =
            data.materials || [];

        materialSelect.innerHTML =
            `<option value="">Select a material</option>`;

        if (materials.length === 0) {

            materialSelect.innerHTML =
                `<option value="">No materials found</option>`;

            quizStatus.textContent =
                "Please upload a PDF first from Study Materials.";

            return;
        }

        materials.forEach(material => {

            const option =
                document.createElement("option");

            option.value =
                material.id;

            option.textContent =
                `${material.filename} (${material.pages} pages)`;

            materialSelect.appendChild(option);

        });

    } catch (error) {

        console.error(
            "Material loading error:",
            error
        );

        quizStatus.textContent =
            "Unable to load study materials.";

    }

}


// Load materials
loadMaterials();


// =====================================================
// GENERATE QUIZ
// =====================================================

generateQuizBtn.addEventListener(
    "click",
    generateQuiz
);


async function generateQuiz() {

    const materialId =
        materialSelect.value;

    const numberOfQuestions =
        Number(questionCount.value);

    const selectedDifficulty =
        difficulty.value;


    if (!materialId) {

        quizStatus.textContent =
            "Please select a study material.";

        return;
    }


    quizStatus.textContent = "";

    quizSetup.style.display =
        "none";

    quizLoading.style.display =
        "block";

    quizContainer.style.display =
        "none";

    quizResult.style.display =
        "none";


    try {

        const response =
            await fetch(
                `${API_URL}/ai/quiz`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({

                        email:
                            user.email,

                        material_id:
                            materialId,

                        number_of_questions:
                            numberOfQuestions,

                        difficulty:
                            selectedDifficulty

                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Quiz generation failed."
            );

        }


        window.currentQuiz =
            data.questions;

        window.currentMaterial =
            data.filename;


        renderQuiz(
            data.questions,
            data.filename,
            data.difficulty
        );


    } catch (error) {

        console.error(
            "Quiz generation error:",
            error
        );

        quizLoading.style.display =
            "none";

        quizSetup.style.display =
            "block";

        quizStatus.textContent =
            error.message ||
            "Something went wrong while generating the quiz.";

    }

}


// =====================================================
// RENDER QUIZ
// =====================================================

function renderQuiz(
    questions,
    filename,
    quizDifficulty
) {

    quizLoading.style.display =
        "none";

    quizContainer.style.display =
        "block";

    quizTitle.textContent =
        `${filename} • ${capitalize(quizDifficulty)} Quiz`;


    questionsContainer.innerHTML = "";


    questions.forEach(
        (question, index) => {

            const questionCard =
                document.createElement("div");

            questionCard.className =
                "question-card";


            const optionsHTML =
                question.options
                    .map(option => {

                        return `
                            <label class="quiz-option">

                                <input
                                    type="radio"
                                    name="question-${index}"
                                    value="${escapeHTML(option)}"
                                >

                                <span>
                                    ${escapeHTML(option)}
                                </span>

                            </label>
                        `;

                    })
                    .join("");


            questionCard.innerHTML = `

                <div class="question-number">
                    Question ${index + 1}
                </div>

                <h3>
                    ${escapeHTML(question.question)}
                </h3>

                <div class="quiz-options">
                    ${optionsHTML}
                </div>

            `;


            questionsContainer.appendChild(
                questionCard
            );

        }
    );


    questionProgress.textContent =
        `${questions.length} Questions`;

}


// =====================================================
// SUBMIT QUIZ + SAVE PROGRESS
// =====================================================

submitQuizBtn.addEventListener(
    "click",
    submitQuiz
);


async function submitQuiz() {

    if (!window.currentQuiz) {
        return;
    }


    let score = 0;


    window.currentQuiz.forEach(
        (question, index) => {

            const selected =
                document.querySelector(
                    `input[name="question-${index}"]:checked`
                );


            const allOptions =
                document.querySelectorAll(
                    `input[name="question-${index}"]`
                );


            allOptions.forEach(input => {

                input.disabled = true;

            });


            if (
                selected &&
                selected.value ===
                question.correct_answer
            ) {

                score++;

                selected.parentElement
                    .classList.add("correct");

            } else {

                if (selected) {

                    selected.parentElement
                        .classList.add("incorrect");

                }


                allOptions.forEach(input => {

                    if (
                        input.value ===
                        question.correct_answer
                    ) {

                        input.parentElement
                            .classList.add("correct");

                    }

                });

            }

        }
    );


    const total =
        window.currentQuiz.length;


    const percentage =
        Math.round(
            (score / total) * 100
        );


    // =================================================
    // SAVE PROGRESS TO MONGODB
    // =================================================

    try {

        const progressResponse =
            await fetch(
                `${API_URL}/progress/quiz`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({

                        email:
                            user.email,

                        filename:
                            window.currentMaterial ||
                            "Unknown",

                        total_questions:
                            total,

                        correct_answers:
                            score,

                        score:
                            score,

                        percentage:
                            percentage,

                        difficulty:
                            difficulty.value

                    })
                }
            );


        const progressData =
            await progressResponse.json();


        if (!progressResponse.ok) {

            throw new Error(
                progressData.detail ||
                "Failed to save quiz progress."
            );

        }


        console.log(
            "Quiz progress saved successfully:",
            progressData
        );


    } catch (error) {

        console.error(
            "Progress save error:",
            error
        );

    }


    // =================================================
    // SHOW RESULT
    // =================================================

    scoreValue.textContent =
        `${score}/${total}`;


    percentageValue.textContent =
        `${percentage}%`;


    if (percentage >= 80) {

        resultMessage.textContent =
            "Excellent work! You have a strong understanding of this topic. 🚀";

    } else if (percentage >= 60) {

        resultMessage.textContent =
            "Good job! A little more revision will make you even stronger. 💪";

    } else {

        resultMessage.textContent =
            "Keep practicing! Review your study material and try again. 📚";

    }


    quizContainer.style.display =
        "none";

    quizResult.style.display =
        "block";


    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

}


// =====================================================
// RESET QUIZ
// =====================================================

function resetQuiz() {

    window.currentQuiz =
        null;

    window.currentMaterial =
        null;

    questionsContainer.innerHTML =
        "";

    quizResult.style.display =
        "none";

    quizContainer.style.display =
        "none";

    quizLoading.style.display =
        "none";

    quizSetup.style.display =
        "block";

    quizStatus.textContent =
        "";

}


restartQuizBtn.addEventListener(
    "click",
    resetQuiz
);


tryAgainBtn.addEventListener(
    "click",
    resetQuiz
);


// =====================================================
// LOGOUT
// =====================================================

logoutBtn.addEventListener(
    "click",
    () => {

        localStorage.removeItem(
            "studyxUser"
        );

        window.location.href =
            "login.html";

    }
);


// =====================================================
// HELPERS
// =====================================================

function capitalize(text) {

    return text.charAt(0).toUpperCase() +
        text.slice(1);

}


function escapeHTML(text) {

    const div =
        document.createElement("div");

    div.textContent =
        text;

    return div.innerHTML;

}