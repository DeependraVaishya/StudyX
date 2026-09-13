const API_URL = "http://127.0.0.1:8000";


// =========================================================
// USER / AUTH
// =========================================================

const user = JSON.parse(
    localStorage.getItem("studyxUser")
);

if (!user) {
    window.location.href = "login.html";
}


// =========================================================
// ELEMENTS
// =========================================================

const userName =
    document.getElementById("userName");

const userEmail =
    document.getElementById("userEmail");

const userAvatar =
    document.getElementById("userAvatar");

const studyGoal =
    document.getElementById("studyGoal");

const subject =
    document.getElementById("subject");

const examDate =
    document.getElementById("examDate");

const dailyHours =
    document.getElementById("dailyHours");

const studyLevel =
    document.getElementById("studyLevel");

const topics =
    document.getElementById("topics");

const generatePlanBtn =
    document.getElementById("generatePlanBtn");

const plannerStatus =
    document.getElementById("plannerStatus");

const plannerSetup =
    document.getElementById("plannerSetup");

const plannerLoading =
    document.getElementById("plannerLoading");

const studyPlan =
    document.getElementById("studyPlan");

const dailyPlan =
    document.getElementById("dailyPlan");

const planTitle =
    document.getElementById("planTitle");

const planSummary =
    document.getElementById("planSummary");

const totalDays =
    document.getElementById("totalDays");

const totalTopics =
    document.getElementById("totalTopics");

const totalHours =
    document.getElementById("totalHours");

const newPlanBtn =
    document.getElementById("newPlanBtn");

const logoutBtn =
    document.getElementById("logoutBtn");


// =========================================================
// CURRENT PLAN
// =========================================================

let currentPlanId =
    localStorage.getItem("studyxPlanId") || "";

let completedTasks = [];


// =========================================================
// USER INFO
// =========================================================

if (user) {

    userName.textContent =
        user.name || "Student";

    userEmail.textContent =
        user.email || "";

    if (user.name) {

        userAvatar.textContent =
            user.name
                .charAt(0)
                .toUpperCase();
    }
}


// =========================================================
// PAGE LOAD
// =========================================================

document.addEventListener(
    "DOMContentLoaded",
    loadSavedPlan
);


// =========================================================
// GENERATE BUTTON
// =========================================================

generatePlanBtn.addEventListener(
    "click",
    generateStudyPlan
);


// =========================================================
// GENERATE STUDY PLAN
// =========================================================

async function generateStudyPlan() {

    const goal =
        studyGoal.value.trim();

    const selectedSubject =
        subject.value.trim();

    const selectedDate =
        examDate.value;

    const hours =
        Number(dailyHours.value);

    const level =
        studyLevel.value;

    const syllabus =
        topics.value.trim();


    // -----------------------------------------------------
    // VALIDATION
    // -----------------------------------------------------

    if (!goal) {

        plannerStatus.textContent =
            "Please enter your study goal.";

        studyGoal.focus();

        return;
    }


    if (!selectedSubject) {

        plannerStatus.textContent =
            "Please enter a subject.";

        subject.focus();

        return;
    }


    if (!selectedDate) {

        plannerStatus.textContent =
            "Please select your target date.";

        examDate.focus();

        return;
    }


    if (!syllabus) {

        plannerStatus.textContent =
            "Please enter your topics or syllabus.";

        topics.focus();

        return;
    }


    plannerStatus.textContent = "";


    // -----------------------------------------------------
    // SHOW LOADING
    // -----------------------------------------------------

    plannerSetup.style.display =
        "none";

    plannerLoading.style.display =
        "block";

    studyPlan.style.display =
        "none";


    try {

        const response =
            await fetch(
                `${API_URL}/ai/study-plan`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        email:
                            user.email,

                        goal:
                            goal,

                        subject:
                            selectedSubject,

                        exam_date:
                            selectedDate,

                        daily_hours:
                            hours,

                        level:
                            level,

                        topics:
                            syllabus
                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Study plan generation failed."
            );
        }


        // -------------------------------------------------
        // SAVE PLAN ID
        // -------------------------------------------------

        currentPlanId =
            data.plan_id || "";

        completedTasks =
            data.completed_tasks || [];


        if (currentPlanId) {

            localStorage.setItem(
                "studyxPlanId",
                currentPlanId
            );
        }


        // -------------------------------------------------
        // SHOW PLAN
        // -------------------------------------------------

        renderStudyPlan(data);


    } catch (error) {

        console.error(
            "Study Planner Error:",
            error
        );


        plannerLoading.style.display =
            "none";

        plannerSetup.style.display =
            "block";


        plannerStatus.textContent =
            error.message ||
            "Unable to generate study plan.";
    }
}


// =========================================================
// LOAD SAVED PLAN
// =========================================================

async function loadSavedPlan() {

    if (!user || !user.email) {
        return;
    }


    try {

        const response =
            await fetch(
                `${API_URL}/study-plans?email=${encodeURIComponent(
                    user.email
                )}`
            );


        if (!response.ok) {
            return;
        }


        const data =
            await response.json();


        if (
            data &&
            Array.isArray(data.plans) &&
            data.plans.length > 0
        ) {

            // Latest plan
            const latestPlan =
                data.plans[0];


            currentPlanId =
                latestPlan.id;


            completedTasks =
                Array.isArray(
                    latestPlan.completed_tasks
                )
                    ? latestPlan.completed_tasks
                    : [];


            localStorage.setItem(
                "studyxPlanId",
                currentPlanId
            );


            renderStudyPlan({

                plan_id:
                    currentPlanId,

                plan:
                    latestPlan.plan,

                completed_tasks:
                    completedTasks

            });
        }


    } catch (error) {

        console.log(
            "Saved plan loading error:",
            error
        );
    }
}


// =========================================================
// RENDER STUDY PLAN
// =========================================================

function renderStudyPlan(data) {

    plannerLoading.style.display =
        "none";

    plannerSetup.style.display =
        "none";

    studyPlan.style.display =
        "block";


    const plan =
        data.plan;


    if (!plan) {

        plannerSetup.style.display =
            "block";

        studyPlan.style.display =
            "none";

        plannerStatus.textContent =
            "No valid study plan found.";

        return;
    }


    if (data.plan_id) {

        currentPlanId =
            data.plan_id;
    }


    if (
        Array.isArray(
            data.completed_tasks
        )
    ) {

        completedTasks =
            data.completed_tasks;
    }


    // -----------------------------------------------------
    // TITLE
    // -----------------------------------------------------

    planTitle.textContent =
        plan.title ||
        "Your Personalized Study Plan";


    // -----------------------------------------------------
    // SUMMARY
    // -----------------------------------------------------

    planSummary.textContent =
        plan.summary ||
        "Your AI-powered study schedule is ready.";


    // -----------------------------------------------------
    // STATS
    // -----------------------------------------------------

    totalDays.textContent =
        Array.isArray(plan.days)
            ? plan.days.length
            : 0;


    let topicCount = 0;

    let hoursCount = 0;


    if (Array.isArray(plan.days)) {

        plan.days.forEach(
            day => {

                if (
                    Array.isArray(
                        day.tasks
                    )
                ) {

                    topicCount +=
                        day.tasks.length;


                    day.tasks.forEach(
                        task => {

                            const taskHours =
                                Number(
                                    task.hours
                                );


                            if (
                                !isNaN(
                                    taskHours
                                )
                            ) {

                                hoursCount +=
                                    taskHours;
                            }
                        }
                    );
                }
            }
        );
    }


    totalTopics.textContent =
        topicCount;

    totalHours.textContent =
        `${hoursCount}h`;


    // -----------------------------------------------------
    // CLEAR PLAN
    // -----------------------------------------------------

    dailyPlan.innerHTML = "";


    if (
        !Array.isArray(plan.days) ||
        plan.days.length === 0
    ) {

        dailyPlan.innerHTML = `
            <div class="question-card">
                No study days were generated.
            </div>
        `;

        return;
    }


    // -----------------------------------------------------
    // RENDER DAYS
    // -----------------------------------------------------

    plan.days.forEach(
        (day, dayIndex) => {

            const dayCard =
                document.createElement(
                    "div"
                );


            dayCard.className =
                "day-plan-card";


            let tasksHTML = "";


            if (
                Array.isArray(day.tasks)
            ) {

                tasksHTML =
                    day.tasks
                        .map(
                            (task, taskIndex) => {

                                const taskKey =
                                    `${dayIndex}-${taskIndex}`;


                                const isCompleted =
                                    completedTasks.includes(
                                        taskKey
                                    );


                                return `

                                    <div
                                        class="study-task ${
                                            isCompleted
                                                ? "task-completed"
                                                : ""
                                        }"
                                        data-day-index="${dayIndex}"
                                        data-task-index="${taskIndex}"
                                    >

                                        <button
                                            type="button"
                                            class="task-check ${
                                                isCompleted
                                                    ? "completed"
                                                    : ""
                                            }"
                                            aria-label="${
                                                isCompleted
                                                    ? "Mark task as pending"
                                                    : "Mark task as completed"
                                            }"
                                        >
                                            ${
                                                isCompleted
                                                    ? "✓"
                                                    : ""
                                            }
                                        </button>


                                        <div class="task-content">

                                            <strong>
                                                ${escapeHTML(
                                                    task.topic ||
                                                    "Study Topic"
                                                )}
                                            </strong>


                                            <p>
                                                ${escapeHTML(
                                                    task.activity ||
                                                    "Study and revise this topic."
                                                )}
                                            </p>

                                        </div>


                                        <span class="task-hours">
                                            ${escapeHTML(
                                                String(
                                                    task.hours || 1
                                                )
                                            )}h
                                        </span>

                                    </div>

                                `;
                            }
                        )
                        .join("");
            }


            dayCard.innerHTML = `

                <div class="day-header">

                    <div class="day-number">
                        ${dayIndex + 1}
                    </div>


                    <div>

                        <span class="day-label">
                            DAY ${dayIndex + 1}
                        </span>


                        <h3>
                            ${escapeHTML(
                                day.date ||
                                `Study Day ${dayIndex + 1}`
                            )}
                        </h3>

                    </div>

                </div>


                <div class="study-tasks">

                    ${tasksHTML}

                </div>

            `;


            dailyPlan.appendChild(
                dayCard
            );
        }
    );


    // -----------------------------------------------------
    // TASK BUTTON EVENTS
    // -----------------------------------------------------

    document
        .querySelectorAll(".task-check")
        .forEach(
            button => {

                button.addEventListener(
                    "click",
                    handleTaskToggle
                );
            }
        );
}


// =========================================================
// TASK COMPLETION
// =========================================================

async function handleTaskToggle(event) {

    const button =
        event.currentTarget;


    const taskElement =
        button.closest(
            ".study-task"
        );


    if (!taskElement) {
        return;
    }


    const dayIndex =
        Number(
            taskElement.dataset.dayIndex
        );


    const taskIndex =
        Number(
            taskElement.dataset.taskIndex
        );


    const taskKey =
        `${dayIndex}-${taskIndex}`;


    const wasCompleted =
        completedTasks.includes(
            taskKey
        );


    const newCompletedState =
        !wasCompleted;


    // -----------------------------------------------------
    // UPDATE LOCAL STATE
    // -----------------------------------------------------

    if (newCompletedState) {

        if (
            !completedTasks.includes(
                taskKey
            )
        ) {

            completedTasks.push(
                taskKey
            );
        }

    } else {

        completedTasks =
            completedTasks.filter(
                key =>
                    key !== taskKey
            );
    }


    // -----------------------------------------------------
    // UPDATE UI
    // -----------------------------------------------------

    updateTaskUI(
        taskElement,
        newCompletedState
    );


    // -----------------------------------------------------
    // CHECK PLAN ID
    // -----------------------------------------------------

    if (!currentPlanId) {

        console.error(
            "Study plan ID is missing."
        );

        return;
    }


    button.disabled = true;


    try {

        const response =
            await fetch(
                `${API_URL}/study-plans/${currentPlanId}/task`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        email:
                            user.email,

                        day_index:
                            dayIndex,

                        task_index:
                            taskIndex,

                        completed:
                            newCompletedState
                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Could not save task status."
            );
        }


        if (
            Array.isArray(
                data.completed_tasks
            )
        ) {

            completedTasks =
                data.completed_tasks;
        }


    } catch (error) {

        console.error(
            "Task save error:",
            error
        );


        // Rollback

        if (newCompletedState) {

            completedTasks =
                completedTasks.filter(
                    key =>
                        key !== taskKey
                );

        } else {

            if (
                !completedTasks.includes(
                    taskKey
                )
            ) {

                completedTasks.push(
                    taskKey
                );
            }
        }


        updateTaskUI(
            taskElement,
            !newCompletedState
        );


        alert(
            "Task status save nahi ho paya. Please try again."
        );

    } finally {

        button.disabled = false;
    }
}


// =========================================================
// UPDATE TASK UI
// =========================================================

function updateTaskUI(
    taskElement,
    completed
) {

    const button =
        taskElement.querySelector(
            ".task-check"
        );


    if (completed) {

        taskElement.classList.add(
            "task-completed"
        );

        button.classList.add(
            "completed"
        );

        button.textContent =
            "✓";

        button.setAttribute(
            "aria-label",
            "Mark task as pending"
        );

    } else {

        taskElement.classList.remove(
            "task-completed"
        );

        button.classList.remove(
            "completed"
        );

        button.textContent =
            "";

        button.setAttribute(
            "aria-label",
            "Mark task as completed"
        );
    }
}


// =========================================================
// NEW PLAN
// =========================================================

newPlanBtn.addEventListener(
    "click",
    () => {

        studyPlan.style.display =
            "none";

        plannerLoading.style.display =
            "none";

        plannerSetup.style.display =
            "block";

        plannerStatus.textContent =
            "";

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }
);


// =========================================================
// LOGOUT
// =========================================================

logoutBtn.addEventListener(
    "click",
    () => {

        localStorage.removeItem(
            "studyxUser"
        );

        localStorage.removeItem(
            "studyxPlanId"
        );

        window.location.href =
            "login.html";
    }
);


// =========================================================
// ESCAPE HTML
// =========================================================

function escapeHTML(text) {

    const div =
        document.createElement(
            "div"
        );

    div.textContent =
        text;

    return div.innerHTML;
}