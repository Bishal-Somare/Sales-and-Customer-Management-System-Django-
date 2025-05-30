// notifications/static/notifications/js/notifications.js
document.addEventListener('DOMContentLoaded', function () {
    const notificationBellDropdown = document.getElementById('notificationBellDropdown'); 
    const notificationBadge = document.getElementById('notificationBadge');
    const notificationList = document.getElementById('notificationList');
    const noNotificationsMessageContainer = document.getElementById('noNotificationsMessageContainer');

    const expiryToggle = document.getElementById('expiryNotificationsToggle');
    const lowStockToggle = document.getElementById('lowStockNotificationsToggle');

    function loadNotificationSettings() {
        if (expiryToggle) {
            expiryToggle.checked = localStorage.getItem('expiryNotificationsEnabled') === 'true';
        }
        if (lowStockToggle) {
            lowStockToggle.checked = localStorage.getItem('lowStockNotificationsEnabled') === 'true';
        }
    }

    function saveNotificationSettings() {
        if (expiryToggle) {
            localStorage.setItem('expiryNotificationsEnabled', expiryToggle.checked);
        }
        if (lowStockToggle) {
            localStorage.setItem('lowStockNotificationsEnabled', lowStockToggle.checked);
        }
    }

    if (expiryToggle) {
        expiryToggle.addEventListener('change', saveNotificationSettings);
    }
    if (lowStockToggle) {
        lowStockToggle.addEventListener('change', saveNotificationSettings);
    }
    
    if (expiryToggle || lowStockToggle) {
        loadNotificationSettings();
    }
    
    let activeNotifications = []; 
    let notificationSocket = null;
    let shakeTimeout = null;

    function connectWebSocket() {
        const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
        notificationSocket = new WebSocket(
            wsScheme + '://' + window.location.host + '/ws/notifications/'
        );

        notificationSocket.onopen = function(e) {
            console.log("Notification WebSocket connected");
        };

        notificationSocket.onmessage = function (e) {
            const data = JSON.parse(e.data);
            if (data.type === 'new_notification') {
                const notification = data.notification;

                const expiryEnabled = localStorage.getItem('expiryNotificationsEnabled') === 'true';
                const lowStockEnabled = localStorage.getItem('lowStockNotificationsEnabled') === 'true';

                let shouldShow = false;
                if ((notification.reason === 'Expiring Soon' || notification.reason === 'Expired') && expiryEnabled) {
                    shouldShow = true;
                }
                if (notification.reason === 'Low Stock' && lowStockEnabled) {
                    shouldShow = true;
                }
                
                if (shouldShow) {
                    addNotification(notification);
                }
            }
        };

        notificationSocket.onclose = function (e) {
            console.error('Notification WebSocket closed. Reconnecting in 5 seconds...');
            setTimeout(connectWebSocket, 5000);
        };

        notificationSocket.onerror = function(err) {
            console.error('Notification WebSocket error:', err.message, 'Closing socket');
            notificationSocket.close(); // This will trigger onclose and attempt reconnection
        };
    }

    function addNotification(notification) {
        // Prevent adding exact duplicate by ID
        if (activeNotifications.find(n => n.id === notification.id)) {
            return; 
        }
        activeNotifications.push(notification);
        // Sort by timestamp in ID for newest first. Assumes ID format "type_itemid_timestamp"
        activeNotifications.sort((a, b) => { 
            const timeA = parseFloat(a.id.substring(a.id.lastIndexOf('_') + 1));
            const timeB = parseFloat(b.id.substring(b.id.lastIndexOf('_') + 1));
            return timeB - timeA;
        });
        renderNotifications();
    }

    function removeNotification(notificationId) {
        activeNotifications = activeNotifications.filter(n => n.id !== notificationId);
        renderNotifications();
    }

    function renderNotifications() {
        if (!notificationList || !notificationBadge || !notificationBellDropdown || !noNotificationsMessageContainer) {
            return; // Elements not present on this page
        }
        
        notificationList.innerHTML = ''; // Clear existing notifications from the list

        if (activeNotifications.length > 0) {
            notificationBadge.textContent = activeNotifications.length;
            notificationBadge.style.display = 'inline-block';
            
            // Shake animation logic
            if (notificationBellDropdown) {
                notificationBellDropdown.classList.remove('shake'); // Remove to reset animation if already there
                // Force reflow/repaint before adding class again for animation to re-trigger
                void notificationBellDropdown.offsetWidth; 
                requestAnimationFrame(() => { // Ensures class removal is processed
                    notificationBellDropdown.classList.add('shake');
                });
                
                if (shakeTimeout) clearTimeout(shakeTimeout); // Clear previous timeout
                // Remove shake class after animation duration to stop continuous shaking
                shakeTimeout = setTimeout(() => {
                    if (notificationBellDropdown) { // Check if element still exists
                         notificationBellDropdown.classList.remove('shake');
                    }
                }, 700); // Should match CSS animation duration for .shake
            }

            noNotificationsMessageContainer.style.display = 'none'; // Hide "no notifications" message

            activeNotifications.forEach(notif => {
                const listItem = document.createElement('li');
                listItem.className = 'notification-item'; 
                listItem.innerHTML = `
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <strong class="notification-reason">${notif.reason}</strong>
                            <span class="notification-message">${notif.message}</span>
                        </div>
                        <button class="btn-close btn-sm ms-2 notification-dismiss" data-id="${notif.id}" aria-label="Dismiss"></button>
                    </div>
                `;
                notificationList.appendChild(listItem);
            });

            // Add event listeners for dismiss buttons
            document.querySelectorAll('.notification-dismiss').forEach(button => {
                button.addEventListener('click', function (event) {
                    event.stopPropagation(); // Prevent dropdown from closing
                    removeNotification(this.dataset.id);
                });
            });

        } else { // No active notifications
            notificationBadge.style.display = 'none';
            if (notificationBellDropdown) {
                notificationBellDropdown.classList.remove('shake');
            }
            noNotificationsMessageContainer.style.display = 'block'; // Show "no notifications" message
        }
    }
    
    renderNotifications(); // Initial render on page load
    
    // Connect WebSocket if the bell dropdown element is present on the page
    if (notificationBellDropdown) {
        connectWebSocket();
    }
});