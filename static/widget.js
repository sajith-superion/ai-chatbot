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

	function getPrevExchange() {
		var nodes = messagesEl.querySelectorAll('.sx-msg');
		var lastUser = null;
		var lastBot = null;
		for (var i = nodes.length - 1; i >= 0 && (lastUser === null || lastBot === null); i--) {
			var n = nodes[i];
			var text = (n.querySelector('.content')?.textContent || '').trim();
			if (!lastBot && n.classList.contains('bot')) {
				// Ignore temporary thinking placeholder
				if (text && !/^\W*thinking\W*$/i.test(text) && text.toLowerCase().indexOf('thinking') === -1) {
					lastBot = text;
				}
			}
			if (!lastUser && n.classList.contains('user')) {
				if (text) lastUser = text;
			}
		}
		return { prev_user_query: lastUser || '', prev_assistant_answer: lastBot || '' };
	}

	async function askBackend(question) {
		try {
			const prev = getPrevExchange();
			const res = await fetch('/ask', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ 
					query: question,
					prev_user_query: prev.prev_user_query,
					prev_assistant_answer: prev.prev_assistant_answer
				})
			});
			const data = await res.json();
			
			if (data && data.answer) {
				return {
					answer: data.answer,
					confidence: data.confidence
				};
			}
			
			if (data && data.error) {
				return {
					answer: 'Error: ' + (data.detail || data.error),
					confidence: 'error'
				};
			}
			
			return {
				answer: 'No response received.',
				confidence: 'error'
			};
		} catch (e) {
			return {
				answer: 'Network error. Please check your connection.',
				confidence: 'error'
			};
		}
	}

	formEl.addEventListener('submit', async function (e) {
		e.preventDefault();
		var q = (inputEl.value || '').trim();
		if (!q) return;
		
		// Add user message
		appendMessage('user', q, false);
		inputEl.value = '';
		
		// Add thinking message
		appendMessage('bot', '🤔 Thinking...', false);
		var thinkingMsg = messagesEl.lastChild;
		
		// Get response from backend
		var response = await askBackend(q);
		
		// Replace thinking message with actual response
		thinkingMsg.querySelector('.content').innerHTML = DOMPurify.sanitize(marked.parse(response.answer || ''));
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

appendMessage('bot', 'Hey! 👋 I\'m your AI business assistant.\nHow can I help you today?', true);
})();
