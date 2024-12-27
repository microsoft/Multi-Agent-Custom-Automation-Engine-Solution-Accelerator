(() => {
  const markdownConverter = new showdown.Converter();
  const apiEndpoint = sessionStorage.getItem("apiEndpoint");
  const taskStore = JSON.parse(sessionStorage.getItem("task"));
  const taskName = document.getElementById("taskName");
  const taskStatusTag = document.getElementById("taskStatusTag");
  const taskStagesMenu = document.getElementById("taskStagesMenu");
  const taskPauseButton = document.getElementById("taskPauseButton");
  const taskAgentsButton = document.getElementById("taskAgentsButton");
  const taskWokFlowButton = document.getElementById("taskWokFlowButton");
  const taskMessageAddButton = document.getElementById("taskMessageAddButton");
  const taskMessages = document.getElementById("taskMessages");
  const taskDetailsAgents = document.getElementById("taskDetailsAgents");
  const taskProgress = document.getElementById("taskProgress");
  const taskProgressPercentage = document.getElementById(
    "taskProgressPercentage"
  );
  const taskProgressBar = document.getElementById("taskProgressBar");
  const taskLoader = document.getElementById("taskLoader");
  const taskAgentsHumans = document.getElementById("taskAgentsHumans");
  const taskStatusDetails = document.getElementById("taskStatusDetails");
  const taskCancelButton = document.getElementById("taskCancelButton");
  const startTaskButtonContainer = document.querySelector(".send-button");
  const startTaskButtonImg = startTaskButtonContainer
    ? startTaskButtonContainer.querySelector("img")
    : null;

  const notyf = new Notyf({
    position: { x: "right", y: "top" },
    ripple: false,
    duration: 3000,
    types: [
      {
        type: "info",
        background: "rgb(71, 80, 235)",
        icon: '<i class="fa-solid fa-circle-info"></i>',
      },
    ],
  });

  const updateButtonImage = () => {
    if (startTaskButtonImg) {
      const newTaskPrompt = document.getElementById("taskMessageTextarea");
      if (newTaskPrompt && newTaskPrompt.value.trim() === "") {
        startTaskButtonImg.src = "../assets/images/air-button.svg";
        startTaskButton.disabled = true;
      } else {
        startTaskButtonImg.src = "/assets/Send.svg";
        startTaskButtonImg.style.width = "16px";
        startTaskButtonImg.style.height = "16px";
        startTaskButton.disabled = false;
      }
    }
  };

  let taskSessionId = null;
  let taskLastStageId = null;
  let taskLastAction = null;
  let taskAgents = [];
  let taskAgentsVsHumans = [];

  const agentToIcon = (agentName) => {
    let agentIcon = "";

    switch (agentName) {
      case "MarketingAgent":
        agentIcon = "unknown";
        break;
      case "HrAgent":
        agentIcon = "hr_agent";
        break;
      case "ExpenseBillingAgent":
        agentIcon = "expense_billing_agent";
        break;
      case "InvoiceReconciliationAgent":
        agentIcon = "invoice_reconciliation_agent";
        break;
      case "TechSupportAgent":
        agentIcon = "tech_agent";
        break;
      case "ProcurementAgent":
        agentIcon = "procurement_agent";
        break;
      case "ProductAgent":
        agentIcon = "product_agent";
        break;
      case "GroupChatManager":
        agentIcon = "manager";
        break;
      case "GenericAgent":
        agentIcon = "manager";
        break;
      case "HumanAgent":
        let userNumber = sessionStorage.getItem("userNumber");
        if (userNumber == null) {
          // Generate a random number between 0 and 6
          userNumber = Math.floor(Math.random() * 6);
          // Create the icon name by concatenating 'user' with the random number
          sessionStorage.setItem("userNumber", userNumber);
        }
        let iconName = "user" + userNumber;
        agentIcon = iconName;
        break;
      case "Done":
        agentIcon = "done";
        break;
      default:
        agentIcon = "marketing_agent";
    }

    return `<img class="is-rounded ${agentIcon}" src="../assets/avatar/${agentIcon}.png" />`;
  };

  const toDateTime = (timestamp) => {
    const date = new Date(timestamp * 1000);
    const options = { month: "short", day: "numeric" };
    const timeOptions = { hour: "numeric", minute: "numeric", hour12: true };
    return `${date.toLocaleDateString(
      "en-US",
      options
    )} at ${date.toLocaleTimeString("en-US", timeOptions)}`;
  };

  const removeClassesExcept = (element, classToKeep) => {
    element.className = classToKeep;
  };

  const handleDisableOfActions = (status) => {
    if(status === "completed"){
      taskPauseButton.disabled=true;
      taskCancelButton.disabled=true;
    } else {
      taskPauseButton.disabled=false;
      taskCancelButton.disabled=false;
    }
  }

  const taskHeaderActions = () => {
    if (taskPauseButton) {
      taskPauseButton.addEventListener("click", (event) => {
        const iconElement = taskPauseButton.querySelector("i");
        if (iconElement) {
          iconElement.classList.toggle("fa-circle-pause");
          iconElement.classList.toggle("fa-circle-play");
          if (iconElement.classList.contains("fa-circle-play")) {
            taskPauseButton.classList.add("has-text-success");
            removeClassesExcept(taskStatusTag, "tag");
            taskStatusTag.classList.add("is-warning");
            taskStatusTag.textContent = "Paused";
          } else {
            taskPauseButton.classList.remove("has-text-success");
            removeClassesExcept(taskStatusTag, "tag");
            taskStatusTag.classList.add("is-info");
            taskStatusTag.textContent = "Restarting";
            taskDetails();
          }
        }
      });
    }

    if (taskCancelButton) {
      taskCancelButton.addEventListener("click", (event) => {
        const apiTaskStore = JSON.parse(sessionStorage.getItem("apiTask"));
        handleDisableOfActions("completed")
        actionStages(apiTaskStore, false);
      });
    }
  };

  const updateTaskDetailsAgents = (agents) => {
    taskDetailsAgents.innerHTML = "";
    taskAgentsVsHumans = [];

    agents.forEach((agent) => {
      const isAvatar = agent === "HumanAgent" ? "is-human" : "is-avatar";

      taskDetailsAgents.innerHTML += `
            <figure class="image is-agent ${isAvatar} is-rounded is-32x32 m-1 has-status has-status-active">
                ${agentToIcon(agent)}
            </figure>
            `;

      agent === "HumanAgent"
        ? taskAgentsVsHumans.push("Human")
        : taskAgentsVsHumans.push("Agent");
    });

    const humansInv = taskAgentsVsHumans.filter((agent) => agent === "Human");
    const humanInvText = humansInv.length > 1 ? "humans" : "human";

    const agentsInv = taskAgentsVsHumans.filter((agent) => agent === "Agent");
    const agentsInvText = agentsInv.length > 1 ? "agents" : "agent";

    taskAgentsHumans.innerHTML = `Team selected: ${humansInv.length} ${humanInvText}, ${agentsInv.length} ${agentsInvText}`;
  };

  const updateTaskStatusDetails = (task) => {
    taskStatusDetails.innerHTML = "";

    taskStatusDetails.innerHTML = `
            <p class="mb-3"><strong>Summary:</strong> ${task.summary}</p>
            <p><strong>Created:</strong> ${toDateTime(task.ts)}</p>
        `;
  };

  const fetchPlanDetails = async (session_id) => {
    console.log("/plans?session_id:", window.headers);

    const headers = await window.headers;

    return fetch(apiEndpoint + "/plans?session_id=" + session_id, {
      method: "GET",
      headers: headers,
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("fetchPlanDetails", data[0]);

        updateTaskStatusDetails(data[0]);
        updateTaskProgress(data[0]);
        fetchTaskStages(data[0]);

        sessionStorage.setItem("apiTask", JSON.stringify(data[0]));
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  };

  const fetchTaskStages = (task) => {
    window.headers.then((headers) => {
      fetch(apiEndpoint + "/steps/" + task.id, {
        method: "GET",
        headers: headers,
      })
        .then((response) => response.json())
        .then((data) => {
          console.log("fetchTaskStages", data);

          if (taskStagesMenu) taskStagesMenu.innerHTML = "";
          let taskStageCount = 0;
          let taskStageApprovalStatus = 0;

          if (data && data.length > 0) {
            taskAgents = [];

            data.forEach((stage) => {
              const stageItem = document.createElement("li");
              const stageBase64 = btoa(
                encodeURIComponent(JSON.stringify(stage))
              );

              let stageStatusIcon = "";
              let stageActions = "";
              let stageRejected = "";

              switch (stage.status) {
                case "planned":
                  stageStatusIcon = `<i class="fa-solid fa-calendar-week mr-2"></i>`;
                  break;
                case "awaiting_feedback":
                  stageStatusIcon = `<i class="fa-solid fa-person-circle-exclamation mr-2 has-text-warning"></i>`;
                  break;
                case "approved":
                  stageStatusIcon = `<i class="fa-solid fa-calendar-check mr-2 has-text-info"></i>`;
                  break;
                case "rejected":
                  stageStatusIcon = `<i class="fa-solid fa-calendar-xmark mr-2 has-text-grey-light"></i>`;
                  break;
                case "action_requested":
                  stageStatusIcon = `<i class="fa-solid fa-calendar-day mr-2 has-text-info fa-beat"></i>`;
                  break;
                case "completed":
                  stageStatusIcon = `<i class="fa-solid fa-calendar-check mr-2 has-text-success"></i>`;
                  break;
                case "failed":
                  stageStatusIcon = `<i class="fa-solid fa-calendar-day mr-2 has-text-danger"></i>`;
                  break;
                default:
                  stageStatusIcon = `<i class="fa-solid fa-calendar-week mr-2"></i>`;
              }

              if (stage.human_approval_status === "rejected") {
                stageRejected = "rejected";
                stageStatusIcon = `<i class="fa-solid fa-calendar-xmark mr-2 has-text-grey-light"></i>`;
              }

              if (stage.human_approval_status === "requested")
                stageActions = `
                                    <div class="menu-stage-actions">
                                        <i title="Approve" class="fa-solid fa-square-check ml-3 menu-stage-action has-text-info" data-action="approved" data-stage="${stageBase64}"></i>
                                        <i title="Reject" class="fa-solid fa-square-xmark ml-1 menu-stage-action" data-action="rejected" data-stage="${stageBase64}"></i>
                                    </div>
                                `;

              stageItem.innerHTML = `
                                <a class="menu-stage ${
                                  stage.status
                                } ${stageRejected}" data-id="${
                stage.id
              }" title="Status: ${stage.status}, Id: ${stage.id}">
                                    ${stageStatusIcon}
                                    <span>${taskStageCount + 1}. ${
                stage.action
              }</span>
                                    ${stageActions}
                                </a>
                                `;

              if (taskStagesMenu) taskStagesMenu.appendChild(stageItem);

              taskSessionId = stage.session_id;
              taskLastStageId = stage.id;
              taskLastAction = stage.action;
              taskAgents.push(stage.agent);

              stageItem
                .querySelectorAll(".menu-stage-action")
                .forEach((action) => {
                  action.addEventListener("click", (event) => {
                    actionStage(
                      event.target.dataset.action,
                      event.target.dataset.stage
                    );

                    action.parentElement.style.display = "none";
                  });
                });

              if (stage.human_approval_status === "requested")
                taskStageApprovalStatus++;

              taskStageCount++;
            });

            updateTaskDetailsAgents([...new Set(taskAgents)]);

            sessionStorage.setItem("showApproveAll", false);

            // Feature approve all removed for this version
            // if (isHumanFeedbackPending()) {
            //     sessionStorage.setItem('showApproveAll', false);
            //     console.log('showApproveAll status', "showApproveAll is false");

            // } else {
            //     sessionStorage.setItem('showApproveAll', taskStageApprovalStatus === taskStageCount);
            //     console.log('showApproveAll status', taskStageApprovalStatus === taskStageCount);

            // }
          }

          fetchTaskMessages(task);

          window.parent.postMessage(
            {
              action: "taskStarted",
            },
            "*"
          );
        })
        .catch((error) => {
          console.error("Error:", error);
        });
    });
  };

  const fetchTaskMessages = (task) => {
    window.headers.then((headers) => {
      fetch(apiEndpoint + "/agent_messages/" + task.session_id, {
        method: "GET",
        headers: headers,
      })
        .then((response) => response.json())
        .then((data) => {
          console.log("fetchTaskMessages", data);

          const toAgentName = (str) => {
            return str.replace(/([a-z])([A-Z])/g, "$1 $2");
          };

          const groupByStepId = (messages) => {
            const groupedMessages = {};

            messages.forEach((message) => {
              const stepId = message.step_id || "planner";
              if (!groupedMessages[stepId]) {
                groupedMessages[stepId] = [];
              }
              groupedMessages[stepId].push(message);
            });

            return groupedMessages;
          };

          const contextFilter = (messages) => {
            const filteredMessages = [];

            messages.forEach((message) => {
              if (
                message.source !== "PlannerAgent" &&
                message.source !== "GroupChatManager"
              ) {
                filteredMessages.push(message);
              }
            });

            return filteredMessages;
          };

          taskMessages.innerHTML = "";

          // console.log(groupByStepId(data));

          if (
            sessionStorage.getItem("context") &&
            sessionStorage.getItem("context") === "customer"
          ) {
            console.log("contextFilter", contextFilter(data));

            data = contextFilter(data);
          }

          if (data) {
            let stageCount = 0;
            let messageCount = 1;
            const groupedData = groupByStepId(data);

            Object.keys(groupedData).forEach((stage) => {
              const messages = groupedData[stage];
              const messageGroupItem = document.createElement("fieldset");

              messageGroupItem.classList.add("task-stage-divider");
              messageGroupItem.classList.add("has-text-info");

              messageGroupItem.innerHTML =
                stageCount === 0
                  ? "<legend>Planning</legend>"
                  : `<legend>Stage ${stageCount}</legend>`;
              taskMessages.appendChild(messageGroupItem);

              messages.forEach((message) => {
                const messageItem = document.createElement("div");
                const showApproveAll =
                  sessionStorage.getItem("showApproveAll") === "true" &&
                  data.length === messageCount;

                let approveAllStagesButton = "";

                messageItem.classList.add("media");
                const isAvatar =
                  message.source === "HumanAgent" ? "is-human" : "is-avatar";
                const isActive =
                  message.source === "PlannerAgent"
                    ? "has-status-busy"
                    : "has-status-active";

                if (
                  sessionStorage.getItem("context") &&
                  sessionStorage.getItem("context") !== "customer"
                ) {
                  if (showApproveAll) {
                    console.log("Creating approveAllStagesButton");
                    approveAllStagesButton = `If you are happy with the plan, you can approve all stages. <br/><button id="approveAllStagesButton" class="button mt-3 is-info">Approve all stages</button>`;
                  }
                }
                const messageLeft = `
                                    <div class="media-left">
                                        <figure
                                            class="image is-agent ${isAvatar} is-rounded is-32x32 m-1 has-status ${isActive}">
                                            ${agentToIcon(message.source)}
                                        </figure>
                                    </div>
                                    <div class="media-content">
                                        <div class="content">
                                            <div class="is-size-7 has-text-weight-medium has-text-grey is-flex">
                                                ${toAgentName(
                                                  message.source
                                                )} • ${toDateTime(
                  message.ts
                )} AI-generated content may be incorrect
                                            </div>
                                            <div class="notification is-light mt-1">
                                                ${markdownConverter.makeHtml(
                                                  message.content
                                                )} ${approveAllStagesButton}
                                            </div>
                                        </div>
                                    </div>
                                    `;
                const messageRight = `
                                    <div class="media-content">
                                        <div class="content">
                                            <div class="is-size-7 has-text-weight-medium has-text-grey is-flex is-justify-content-end">
                                                You • ${toDateTime(message.ts)}
                                            </div>
                                            <div class="notification is-info is-light mt-1 is-pulled-right">
                                                ${markdownConverter.makeHtml(
                                                  message.content
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                    <div class="media-right">
                                        <figure
                                            class="image is-agent ${isAvatar} is-rounded is-32x32 m-1 has-status has-status-active">
                                            ${agentToIcon(message.source)}
                                        </figure>
                                    </div>
                                    `;

                const messageTemplate =
                  message.source === "HumanAgent" ? messageRight : messageLeft;
                messageItem.innerHTML = messageTemplate;
                taskMessages.appendChild(messageItem);

                if (
                  sessionStorage.getItem("context") &&
                  sessionStorage.getItem("context") !== "customer"
                ) {
                  if (showApproveAll) {
                    document
                      .getElementById("approveAllStagesButton")
                      .addEventListener("click", (event) =>
                        actionStages(task, true)
                      );
                  }
                }

                messageCount++;
              });

              stageCount++;
            });

            const mediaContents = document.querySelectorAll(".media-content");
            if (mediaContents.length > 0) {
              mediaContents[mediaContents.length - 1].scrollIntoView({
                behavior: "smooth",
              });
            }

            if (
              sessionStorage.getItem("context") &&
              sessionStorage.getItem("context") === "customer" &&
              !sessionStorage
                .getItem("actionStagesRun")
                .includes(task.session_id)
            ) {
              actionStages(task, true);

              let actionStagesRun = JSON.parse(
                sessionStorage.getItem("actionStagesRun") || "[]"
              );

              actionStagesRun.push(task.session_id);
              sessionStorage.setItem(
                "actionStagesRun",
                JSON.stringify(actionStagesRun)
              );
            }

            setTimeout(() => {
              taskLoader.classList.add("is-hidden");
            }, 500);
          }
        })
        .catch((error) => {
          console.error("Error:", error);
        });
    });
  };

  const updateTaskProgress = (task) => {
    const taskStatusToLabel = (str) => {
      return str
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
    };

    const totalSteps = task.total_steps;
    const completedSteps = task.completed;
    const approvalRequired = task.steps_requiring_approval;

    const percentage = (completedSteps / totalSteps) * 100;
    const progressString = `Progress ${completedSteps}/${totalSteps}`;
    const percentageString = `${percentage.toFixed(0)}%`;

    taskProgress.textContent = progressString;
    taskProgressPercentage.textContent = percentageString;
    taskProgressBar.value = parseFloat(percentageString);

    taskStatusTag.textContent = taskStatusToLabel(task.overall_status);

    if (task.overall_status === "completed") {
      removeClassesExcept(taskStatusTag, "tag");
      taskStatusTag.classList.add("is-success");
    } else if (task.overall_status === "in_progress") {
      removeClassesExcept(taskStatusTag, "tag");
      taskStatusTag.classList.add("is-info");
    }
    handleDisableOfActions(task.overall_status)
  };

  const isHumanFeedbackPending = () => {
    const storedData = sessionStorage.getItem("apiTask");
    const planDetails = JSON.parse(storedData);
    return (
      planDetails.human_clarification_request !== null &&
      planDetails.human_clarification_response === null
    );
  };

  const actionStage = (action, stage) => {
    if (isHumanFeedbackPending()) {
      notyf.error("You must first provide feedback to the planner.");
      return;
    }

    const stageObj = JSON.parse(decodeURIComponent(atob(stage)));

    console.log("actionStage", {
      step_id: stageObj.id,
      plan_id: stageObj.plan_id,
      session_id: stageObj.session_id,
      approved: action === "approved" ? true : false,
    });

    notyf.open({
      type: "info",
      message: `Request sent for "${stageObj.action}"`,
    });

    window.headers.then((headers) => {
      fetch(apiEndpoint + "/approve_step_or_steps", {
        method: "POST",
        headers: headers,
        body: JSON.stringify({
          step_id: stageObj.id,
          plan_id: stageObj.plan_id,
          session_id: stageObj.session_id,
          approved: action === "approved" ? true : false,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          console.log("actionStage", data);
          action === "approved"
            ? notyf.success(`Stage "${stageObj.action}" approved.`)
            : notyf.error(`Stage "${stageObj.action}" rejected.`);

          taskDetails();
        })
        .catch((error) => {
          console.error("Error:", error);
        });
    });
  };

  const actionStages = (task, approve) => {
    console.log("approveStages", {
      plan_id: task.id,
      session_id: task.session_id,
      approved: approve,
    });

    notyf.open({
      type: "info",
      message: `Request sent to action on all stages.`,
    });

    // document.querySelectorAll('.menu-stage-actions').forEach(element => {
    //     element.style.display = 'none';
    // });

    window.headers.then((headers) => {
      fetch(apiEndpoint + "/approve_step_or_steps", {
        method: "POST",
        headers: headers,
        body: JSON.stringify({
          plan_id: task.id,
          session_id: task.session_id,
          approved: approve,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          console.log("approveStages", data);
          approve
            ? notyf.success(`All stages approved.`)
            : notyf.error(`All stages cancelled.`);
          taskDetails();
        })
        .catch((error) => {
          console.error("Error:", error);
        });
    });
  };

  const taskDetailsActions = () => {
    if (taskAgentsButton) {
      taskAgentsButton.addEventListener("click", (event) => {
        window.parent.postMessage(
          {
            button: "taskAgentsButton",
            id: taskStore.id,
            name: taskStore.name,
          },
          "*"
        );
      });
    }

    if (taskWokFlowButton) {
      taskWokFlowButton.addEventListener("click", (event) => {
        window.parent.postMessage(
          {
            button: "taskWokFlowButton",
            id: taskStore.id,
            name: taskStore.name,
          },
          "*"
        );
      });
    }
  };

  let lastDataHash = null;
  //Refresh timer
  const taskDetails = () => {
    if (taskStore) {
      taskName.innerHTML = taskStore.name;

      const fetchLoop = async (id) => {
        try {
          // Fetch the new data from the server
          const newData = await fetchPlanDetails(id);

          // Generate a hash of the new data
          const newDataHash = await GenerateHash(newData);

          // Check if the new data's hash is different from the last fetched data's hash
          if (newDataHash === lastDataHash) {
            console.log("Data hasn't changed. Skipping next poll.");
            return; // Skip polling if no changes
          }

          // Update the lastDataHash to the new hash
          lastDataHash = newDataHash;

          // Continue polling by calling fetchLoop again
          setTimeout(
            () => fetchLoop(id),
            Number(sessionStorage.getItem("apiRefreshRate"))
          );
        } catch (error) {
          console.error("Error in fetchLoop:", error);
        }
      };

      fetchLoop(taskStore.id); // Start the fetch loop
    }
  };

  const taskMessage = () => {
    const taskMessageTextarea = document.getElementById("taskMessageTextarea");

    if (taskMessageAddButton) {
      taskMessageAddButton.addEventListener("click", (event) => {
        const messageContent = taskMessageTextarea.value;

        if (!messageContent) {
          notyf.error("Please enter a message.");
          return;
        }

        taskMessageTextarea.disabled = true;
        taskMessageAddButton.disabled = true;
        taskMessageAddButton.classList.add("is-loading");

        console.log({
          plan_id: taskStore.id,
          session_id: taskSessionId,
          human_clarification: taskMessageTextarea.value,
        });

        window.headers.then((headers) => {
          fetch(apiEndpoint + "/human_clarification_on_plan", {
            method: "POST",
            headers: headers,
            body: JSON.stringify({
              plan_id: taskStore.id,
              session_id: taskSessionId,
              human_clarification: taskMessageTextarea.value,
            }),
          })
            .then((response) => response.json())
            .then((data) => {
              console.log("taskMessage", data);

              taskMessageTextarea.disabled = false;
              taskMessageAddButton.disabled = false;
              taskMessageAddButton.classList.remove("is-loading");

              taskMessageTextarea.value = "";
              fetchPlanDetails(taskStore.id);

              // Reset character count to 0
              const charCount = document.getElementById("charCount");
              if (charCount) {
                charCount.textContent = "0";
              }
              updateButtonImage();
              
              notyf.success("Additional details registered in plan.");
            })
            .catch((error) => {
              console.error("Error:", error);
            });
        });
      });
    }
  };

  const handleTextAreaTyping = () => {
    const newTaskPrompt = document.getElementById("taskMessageTextarea");
    newTaskPrompt.addEventListener("input", () => {
      // whenever text is sent to the text area, we want to update the character count and dynamically resize the text area
      const textInput = document.getElementById("taskMessageTextarea");
      const charCount = document.getElementById("charCount");

      // Update character count
      charCount.textContent = textInput.value.length;

      // Dynamically adjust height
      textInput.style.height = "auto";
      textInput.style.height = textInput.scrollHeight + "px";
      updateButtonImage();
    });
    newTaskPrompt.addEventListener("keydown", (event) => {
      const textValue = newTaskPrompt.value.trim();
      if (event.key === "Enter" && !event.shiftKey) {
        if (textValue === "") {
          event.preventDefault();
        } else {
          startTaskButton.click();
        }
      } else if (event.key === "Enter" && event.shiftKey) {
        return;
      }
    });
  };
  updateButtonImage();
  taskHeaderActions();
  taskDetailsActions();
  taskDetails();
  taskMessage();
  handleTextAreaTyping();
})();
