(() => {
    window.headers = GetAuthDetails();
    const apiEndpoint = getStoredData('apiEndpoint') || BACKEND_API_URL;
    const goHomeButton = document.getElementById("goHomeButton");
    const newTaskButton = document.getElementById("newTaskButton");
    const closeModalButtons = document.querySelectorAll(".modal-close-button");
    const myTasksMenu = document.getElementById("myTasksMenu");
    const tasksStats = document.getElementById("tasksStats");

    //if (!sessionStorage.getItem('apiEndpoint')) setStoredData('apiEndpoint', apiEndpoint);
    // Force rewrite of apiEndpoint
    setStoredData('apiEndpoint', apiEndpoint);
    setStoredData('context', 'employee');
    // Refresh rate is set
    if (!getStoredData('apiRefreshRate')) setStoredData('apiRefreshRate', 5000);
    if (!getStoredData('actionStagesRun')) setStoredData('actionStagesRun', []);

    const getQueryParam = (param) => {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    };

    const setQueryParam = (param, value) => {
        const urlParams = new URLSearchParams(window.location.search);
        urlParams.set(param, value);
        window.history.replaceState(null, null, `?${urlParams.toString()}`);
    };

    const switchView = () => {
        const viewIframe = document.getElementById('viewIframe');
        if (viewIframe) {
            const viewRoute = getQueryParam('v');
            const viewContext = getStoredData('context');
            const noCache = '?nocache=' + new Date().getTime();
            switch (viewRoute) {
                case 'home':
                    viewIframe.src = 'home/home.html' + noCache;
                    break;
                case 'task':
                    viewIframe.src = `task/${viewContext}.html` + noCache;
                    break;
                default:
                    viewIframe.src = 'home/home.html';
            }
        }
    };
    // get user session 
    const getUserInfo = async () => {
        if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
            // Runninng in Azure so get user info from /.auth/me
          try {
              const response = await fetch('/.auth/me');
              if (!response.ok) {
                  console.log("No identity provider found. Access to chat will be blocked.");
                  return null;
              }
              const payload = await response.json();

              if (payload) {
                  return payload;
              }
              return null;
            } catch (e) {
                console.error("Error fetching user info:", e);
                return null;
            }
        } else {
            // Running locally so use a mock user
            return {
                name: 'Local User',
                authenticated: true
            }
        }
    };

    const homeActions = () => {
        if (newTaskButton && goHomeButton) {
            newTaskButton.addEventListener('click', (event) => {
                event.preventDefault();
                setQueryParam('v', 'home');
                switchView();
            });
    
            goHomeButton.addEventListener('click', (event) => {
                event.preventDefault();
                setQueryParam('v', 'home');
                switchView();
            });
        }
    };

    const messageListeners = () => {

        window.addEventListener('message', (event) => {
            if (event.data && event.data.button) {
                if (event.data.button === 'taskAgentsButton') taskAgentsModal.classList.add('is-active');
                if (event.data.button === 'taskWokFlowButton') taskWokFlowModal.classList.add('is-active');
            }
            if (event.data && event.data.action) {
                if (event.data.action === 'taskStarted') fetchTasksIfNeeded();
            }
        });

    }

    const getMyTasks = () => {
        myTasksMenu.innerHTML = `
            <div class="notification">
                <i class="fa-solid fa-circle-notch fa-spin mr-3"></i> Loading tasks...
            </div>
        `;
    }

    const fetchTasksIfNeeded = async () => {
        const taskStore = JSON.parse(getStoredData('task'));
        window.headers
            .then(headers => {
                fetch(apiEndpoint + '/plans', {
                    method: 'GET',
                    headers: headers,
                })
                    .then(response => response.json())
                    .then(data => {
        
                        if (myTasksMenu){
                            myTasksMenu.innerHTML = '';
                        }
        
                        if (data && data.length > 0) {
        
                            const lastFiveTasks = data.slice(-5);
                            let taskCount = 1;
                            let inProgressTaskCount = 0;
                            let inCompletedTaskCount = 0;
                            let stagesPlannedCount = 0;
                            let stagesRejectedCount = 0;
        
                            lastFiveTasks.forEach(task => {
                                const newTaskItem = document.createElement('li');
                                const completedSteps = task.completed;
                                let taskActive = '';
        
                                if (taskStore && taskStore.id === task.session_id) taskActive = 'is-active';
        
                                const taskStatus = (task.overall_status === 'completed') ? '<i class="fa-solid fa-check-to-slot has-text-success mr-3"></i>' : '<i class="fa-solid fa-arrows-rotate fa-spin mr-3"></i>';
        
                                newTaskItem.innerHTML = `
                                <a href class="menu-task ${taskActive}" data-name="${task.initial_goal}" data-id="${task.session_id}" title="Status: ${task.overall_status}, Session id: ${task.session_id} ">
                                    ${taskStatus}
                                    <span>${taskCount}.  ${task.initial_goal}</span>
                                    <div class="tag is-dark ml-3">${completedSteps}/${task.total_steps}</div>
                                </a>
                                `;
                                
                                if(myTasksMenu){
                                    myTasksMenu.appendChild(newTaskItem);
                                }
        
                                newTaskItem.querySelector('.menu-task').addEventListener('click', (event) => {
                                    const sessionId = event.target.closest('.menu-task').dataset.id;
                                    const taskName = event.target.closest('.menu-task').dataset.name;
        
                                    event.preventDefault();
                                    setQueryParam('v', 'task');
                                    switchView();
        
                                    setStoredData('task', JSON.stringify({
                                        id: sessionId,
                                        name: taskName
                                    }));
        
                                    document.querySelectorAll('.menu-task').forEach(task => {
                                        task.classList.remove('is-active');
                                    });
        
                                    event.target.closest('.menu-task').classList.add('is-active');
                                });
        
                                if (task.overall_status === 'completed') inCompletedTaskCount++;
                                if (task.overall_status !== 'completed') inProgressTaskCount++;
                                if (task.overall_status === 'planned') stagesPlannedCount++;
                                if (task.overall_status === 'rejected') stagesRejectedCount++;
        
                                const addS = (word, count) => (count === 1) ? word : word + 's';
                                
                                if(tasksStats){
                                    tasksStats.innerHTML = `
                                        <li><a><strong>${inCompletedTaskCount}</strong> ${addS('task', inCompletedTaskCount)} completed</a></li>
                                        <li><a><strong>${inProgressTaskCount}</strong> ${addS('task', inProgressTaskCount)} in progress</a></li>
                                    `;
                                }
        
                                taskCount++;
        
                            })
        
        
                        }
        
                    })
                    .catch(error => {
                        console.error('Error:', error);
                    })

    })
       
    };

    const modalActions = () => {
        closeModalButtons.forEach(closeModalButton => {
            closeModalButton.addEventListener('click', (event) => {
                event.preventDefault();
                const modal = closeModalButton.closest('.modal');
                modal.classList.remove('is-active');
            });
        });
    };

    const initializeApp = async () => {
        // Fetch user info when the app loads
        const userInfo = await getUserInfo();
        if (!userInfo) {
            console.error("Authentication failed. Access to tasks is restricted.");
        } else {
            setStoredData('userInfo', userInfo);
            await fetchTasksIfNeeded();  // Fetch tasks after initialization if needed
        }
    };

    fetchTasksIfNeeded();
    initializeApp();
    homeActions();
    switchView();
    messageListeners();
    modalActions();
})();
