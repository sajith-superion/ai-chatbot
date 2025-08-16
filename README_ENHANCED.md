# 🚀 Enhanced AI Chatbot

A sophisticated AI-powered chatbot with advanced RAG capabilities, conversation memory, and intelligent out-of-scope detection.

## ✨ New Features

### 🧠 **Enhanced RAG (Retrieval-Augmented Generation)**
- **Contextual Compression**: Automatically extracts and compresses relevant information from documents
- **Improved Search**: Better document retrieval with similarity scoring and threshold filtering
- **Source Citations**: Shows which documents were used to generate answers
- **Confidence Scoring**: Indicates how confident the system is in its responses

### 💬 **Conversation Memory**
- **Session Management**: Maintains conversation context across multiple questions
- **Context-Aware Responses**: Uses previous messages to provide better, contextual answers
- **Conversation History**: API endpoints to retrieve and manage chat sessions
- **Memory Optimization**: Automatically limits conversation history to prevent memory bloat

### 🚫 **Out-of-Scope Detection**
- **Intelligent Filtering**: Automatically detects questions outside your knowledge base
- **Business Focus**: Specifically trained on business strategy, EUC ecosystem, go-to-market, pricing, PLG, market research, SaaS operations, and distributed work
- **Polite Redirection**: Guides users back to topics you can help with
- **Confidence Indicators**: Clear visual feedback on response quality

### 🎨 **Enhanced UI/UX**
- **Confidence Indicators**: Visual badges showing response confidence levels
- **Source Citations**: Displays document sources used for answers
- **Better Styling**: Improved visual design with hover effects and transitions
- **Responsive Design**: Works great on all device sizes

## 🏗️ Architecture Improvements

### **Enhanced Document Processing**
- Larger chunk sizes (1000 vs 500) for better context
- Increased overlap (200 vs 50) for continuity
- Better text splitting with custom separators
- Improved FAISS search parameters

### **Advanced Retrieval System**
- **Contextual Compression Retriever**: Uses LLM to compress and focus relevant information
- **Similarity Score Threshold**: Only returns documents above confidence threshold
- **Multi-stage Retrieval**: Fetches more candidates before filtering for quality

### **Better LLM Integration**
- Lower temperature (0.1) for more consistent responses
- Enhanced prompts with conversation context
- Out-of-scope classification using dedicated chain

## 🚀 Getting Started

### 1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 2. **Set Environment Variables**
Create a `.env` file:
```env
OPENROUTER_API_KEY=your_api_key_here
# or
OPENAI_API_KEY=your_openai_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

### 3. **Run the Chatbot**
```bash
uvicorn chatbot:app --reload
```

### 4. **Test Enhanced Features**
```bash
python test_enhanced_chatbot.py
```

## 📡 API Endpoints

### **Enhanced Chat Endpoint**
```http
POST /ask
Content-Type: application/json

{
  "query": "Your question here",
  "session_id": "optional_session_id"
}
```

**Response:**
```json
{
  "answer": "AI-generated response with markdown formatting",
  "sources": "📄 Source 1: document_name.pdf\n📄 Source 2: another_doc.docx",
  "confidence": "high|medium|out_of_scope|error",
  "session_id": "unique_session_identifier"
}
```

### **Conversation Management**
```http
GET /conversation/{session_id}     # Get conversation history
DELETE /conversation/{session_id}   # Clear conversation history
```

## 🔧 Configuration Options

### **RAG Parameters**
- **Chunk Size**: 1000 characters (configurable)
- **Chunk Overlap**: 200 characters (configurable)
- **Search Threshold**: 0.5 similarity score
- **Max Documents**: 8 per query
- **Fetch Candidates**: 20 before filtering

### **Memory Settings**
- **Max Messages**: 20 per session
- **Context Window**: Last 5 messages for context
- **Session TTL**: In-memory (add Redis for production)

## 🧪 Testing

Run the comprehensive test suite:
```bash
python test_enhanced_chatbot.py
```

This tests:
1. ✅ In-scope business questions
2. ✅ Conversation memory and follow-ups
3. ✅ Out-of-scope detection
4. ✅ Conversation history management
5. ✅ Session cleanup

## 🎯 Use Cases

### **Business Intelligence**
- Market research analysis
- Competitive landscape insights
- Strategy recommendations
- Pricing strategy guidance

### **Knowledge Management**
- Document Q&A with citations
- Contextual information retrieval
- Multi-turn conversations
- Source verification

### **Customer Support**
- Intelligent question routing
- Context-aware responses
- Out-of-scope detection
- Professional redirection

## 🚀 Production Considerations

### **Scalability**
- Replace in-memory storage with Redis
- Add load balancing for multiple instances
- Implement connection pooling
- Add rate limiting and quotas

### **Security**
- Add user authentication
- Implement API key management
- Add request logging and monitoring
- Content filtering and moderation

### **Monitoring**
- Response quality metrics
- User satisfaction tracking
- Performance monitoring
- Error tracking and alerting

## 🔮 Future Enhancements

- **Multi-modal Support**: Image and audio processing
- **Advanced Analytics**: Usage insights and conversation quality metrics
- **Integration APIs**: Webhook support and third-party integrations
- **Personalization**: User preferences and custom knowledge bases
- **Multi-language Support**: Internationalization capabilities

## 📊 Performance Metrics

- **Response Time**: Typically 2-5 seconds
- **Accuracy**: Improved with contextual compression
- **Memory Usage**: Optimized with conversation limits
- **Scalability**: Ready for horizontal scaling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built with ❤️ using FastAPI, LangChain, and modern AI technologies**
