(function () {
	var messagesEl = document.getElementById('messages');
	var inputEl = document.getElementById('user-input');
	var formEl = document.getElementById('chat-form');
	var closeBtn = document.querySelector('.sx-close');

function appendMessage(role, text, isMarkdown) {
    var div = document.createElement('div');
    div.className = 'sx-msg ' + (role === 'user' ? 'user' : 'bot');
    var content = document.createElement('div');
    content.className = 'content';
    if (isMarkdown) {
        try {
            var html = marked.parse(text || '');
            content.innerHTML = DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });
        } catch (e) {
            content.textContent = text;
        }
    } else {
        content.textContent = text;
    }
    div.appendChild(content);
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

	async function askBackend(question) {
		try {
			const res = await fetch('/ask', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ query: question })
			});
			const data = await res.json();
			if (data && data.answer) return data.answer;
			if (data && data.error) return 'Error: ' + (data.detail || data.error);
			return 'No response.';
		} catch (e) {
			return 'Network error.';
		}
	}

	formEl.addEventListener('submit', async function (e) {
		e.preventDefault();
		var q = (inputEl.value || '').trim();
		if (!q) return;
    appendMessage('user', q, false);
		inputEl.value = '';
    appendMessage('bot', 'Thinking...', false);
		var tmp = messagesEl.lastChild;
		var ans = await askBackend(q);
    tmp.querySelector('.content').innerHTML = DOMPurify.sanitize(marked.parse(ans || ''));
	});

closeBtn.addEventListener('click', function () {
    try {
        // If embedded, notify parent to close
        if (window.parent && window.parent !== window) {
            window.parent.postMessage('superion:close', '*');
        } else {
            // Standalone: hide app and show standalone icon if present
            var app = document.getElementById('app');
            app.style.display = 'none';
            var toggles = document.getElementsByClassName('sx-standalone-toggle');
            if (toggles && toggles[0]) toggles[0].style.display = 'flex';
        }
    } catch (e) {
        // Fallback to hiding in standalone
        var app = document.getElementById('app');
        if (app) app.style.display = 'none';
    }
});

appendMessage('bot', 'Hey! Need any help?', true);
})();
