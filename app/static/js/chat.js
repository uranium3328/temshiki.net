const socket = io();

// Подключаемся к комнате
socket.emit('join', { room: ROOM_ID });

// Прокрутка вниз
function scrollToBottom() {
    const el = document.getElementById('chat-messages');
    if (el) el.scrollTop = el.scrollHeight;
}
scrollToBottom();

// Отправка сообщения
const form = document.getElementById('message-form');
const input = document.getElementById('message-input');

form.addEventListener('submit', function (e) {
    e.preventDefault();
    const content = input.value.trim();
    if (!content) return;
    socket.emit('send_message', { room: ROOM_ID, content: content });
    input.value = '';
    input.focus();
});

// Ctrl+Enter тоже отправляет
input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        form.dispatchEvent(new Event('submit'));
    }
});

// Получение сообщения
socket.on('receive_message', function (data) {
    const container = document.getElementById('chat-messages');

    // Убираем заглушку если есть
    const empty = container.querySelector('.text-center.text-muted');
    if (empty) empty.remove();

    const isOwn = data.sender_id === CURRENT_USER_ID;
    const row = document.createElement('div');
    row.className = 'message-row ' + (isOwn ? 'own' : 'other');

    row.innerHTML = `
        <div class="message-bubble ${data.is_bot ? 'is-bot' : ''}">
            ${data.is_bot ? '<div class="bot-badge"><i class="bi bi-robot"></i> Автоответ</div>' : ''}
            <div class="message-content">${escapeHtml(data.content)}</div>
            <div class="message-time">${data.created_at}</div>
        </div>
    `;
    container.appendChild(row);
    scrollToBottom();
});

function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

// Уведомление при потере фокуса
socket.on('connect', () => console.log('Chat connected'));
socket.on('disconnect', () => console.log('Chat disconnected'));
