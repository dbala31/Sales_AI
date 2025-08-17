from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import os

from app.api import upload, verification, mock_data
from app.core.database import engine, Base
from app.utils.logger import setup_logger
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Sales AI Contact Verification Platform")
    
    # Setup logging
    setup_logger()
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    # Create necessary directories
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Sales AI Contact Verification Platform")


# Create FastAPI application
app = FastAPI(
    title="Sales AI Contact Verification Platform",
    description="AI-powered contact verification system for sales teams",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(upload.router)
app.include_router(verification.router)
app.include_router(mock_data.router)

# Mount static files for web interface
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web interface"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sales AI Contact Verification</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #2c3e50;
                text-align: center;
                margin-bottom: 30px;
            }
            .feature-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }
            .feature-card {
                border: 1px solid #ddd;
                padding: 20px;
                border-radius: 8px;
                background: #fafafa;
            }
            .feature-card h3 {
                color: #34495e;
                margin-top: 0;
            }
            .upload-area {
                border: 2px dashed #3498db;
                padding: 40px;
                text-align: center;
                border-radius: 8px;
                background: #ecf0f1;
                margin: 20px 0;
            }
            .btn {
                background: #3498db;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                text-decoration: none;
                display: inline-block;
            }
            .btn:hover {
                background: #2980b9;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .stat-card {
                background: #34495e;
                color: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
            }
            .stat-number {
                font-size: 24px;
                font-weight: bold;
                display: block;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Sales AI Contact Verification Platform</h1>
            
            <div class="upload-area">
                <h3>📥 Upload CSV File for Contact Verification</h3>
                <p>Upload your contact list and we'll verify each contact using our free verification pipeline</p>
                <input type="file" id="csvFile" accept=".csv" style="margin: 10px;">
                <br><br>
                <button class="btn" onclick="uploadFile()">Start Verification</button>
                <br><br>
                <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px;">
                    <h4>🧪 Mock Data for Testing</h4>
                    <p>Test the platform with sample data:</p>
                    <button class="btn" onclick="downloadSampleData()" style="background: #28a745; margin-right: 10px;">Download Sample CSV</button>
                    <button class="btn" onclick="uploadMockSalesforce()" style="background: #17a2b8;">Upload Mock Salesforce Data</button>
                    <input type="file" id="mockSalesforceFile" accept=".csv" style="display: none;">
                </div>
            </div>
            
            <div class="stats" id="stats">
                <div class="stat-card">
                    <span class="stat-number" id="totalContacts">-</span>
                    <span>Total Contacts</span>
                </div>
                <div class="stat-card">
                    <span class="stat-number" id="verifiedContacts">-</span>
                    <span>Verified Contacts</span>
                </div>
                <div class="stat-card">
                    <span class="stat-number" id="verificationRate">-</span>
                    <span>Success Rate</span>
                </div>
                <div class="stat-card">
                    <span class="stat-number" id="avgQuality">-</span>
                    <span>Avg Quality Score</span>
                </div>
            </div>
            
            <div class="feature-grid">
                <div class="feature-card">
                    <h3>📧 Free Email Verification</h3>
                    <p>RFC 5322 validation + DNS/MX lookup + SMTP RCPT TO verification - no paid APIs needed</p>
                </div>
                
                <div class="feature-card">
                    <h3>⚡ Fast Processing</h3>
                    <p>Streamlined verification pipeline optimized for speed and accuracy</p>
                </div>
                
                <div class="feature-card">
                    <h3>📱 Enhanced Phone Validation</h3>
                    <p>libphonenumber validation with business/mobile classification and normalization</p>
                </div>
                
                <div class="feature-card">
                    <h3>🤖 AI-Powered Analysis</h3>
                    <p>Gemini 2.0 Flash integration for enhanced contact quality assessment and insights</p>
                </div>
                
                <div class="feature-card">
                    <h3>⚡ Batch Processing</h3>
                    <p>Process thousands of contacts simultaneously with intelligent queuing and rate limiting</p>
                </div>
                
                <div class="feature-card">
                    <h3>📊 Salesforce Integration</h3>
                    <p>Deduplication and enrichment with mock data support for testing without API access</p>
                </div>
            </div>
            
            <div style="margin-top: 30px; text-align: center;">
                <a href="/docs" class="btn">View API Documentation</a>
                <a href="/api/verification/statistics" class="btn" style="margin-left: 10px;">Get Statistics</a>
            </div>
        </div>
        
        <script>
            // Load statistics on page load
            async function loadStats() {
                try {
                    const response = await fetch('/api/verification/statistics');
                    const stats = await response.json();
                    
                    document.getElementById('totalContacts').textContent = stats.contacts.total.toLocaleString();
                    document.getElementById('verifiedContacts').textContent = stats.contacts.verified.toLocaleString();
                    document.getElementById('verificationRate').textContent = stats.contacts.verification_rate + '%';
                    document.getElementById('avgQuality').textContent = stats.quality_scores.average;
                } catch (error) {
                    console.error('Error loading statistics:', error);
                }
            }
            
            async function uploadFile() {
                const fileInput = document.getElementById('csvFile');
                const file = fileInput.files[0];
                
                if (!file) {
                    alert('Please select a CSV file first');
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    const response = await fetch('/api/upload/csv', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        alert(`Upload successful! Batch ID: ${result.batch_id}\\nProcessing ${result.total_contacts} contacts...`);
                        // Reload stats after upload
                        setTimeout(loadStats, 2000);
                    } else {
                        alert('Upload failed: ' + result.detail);
                    }
                } catch (error) {
                    alert('Upload error: ' + error.message);
                }
            }
            
            async function downloadSampleData() {
                try {
                    const response = await fetch('/api/mock/sample-data/download');
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'sample_contacts.csv';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(url);
                    } else {
                        alert('Failed to download sample data');
                    }
                } catch (error) {
                    alert('Download error: ' + error.message);
                }
            }
            
            function uploadMockSalesforce() {
                document.getElementById('mockSalesforceFile').click();
            }
            
            document.getElementById('mockSalesforceFile').addEventListener('change', async function(event) {
                const file = event.target.files[0];
                if (!file) return;
                
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    const response = await fetch('/api/mock/salesforce/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        alert(`Mock Salesforce data uploaded successfully!\\n${JSON.stringify(result.statistics, null, 2)}`);
                    } else {
                        alert('Upload failed: ' + result.detail);
                    }
                } catch (error) {
                    alert('Upload error: ' + error.message);
                }
            });
            
            // Load stats when page loads
            loadStats();
        </script>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Sales AI Contact Verification Platform",
        "version": "1.0.0"
    }


@app.exception_handler(404)
async def not_found_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=404, content={"detail": "Endpoint not found"})


@app.exception_handler(500)
async def server_error_handler(request, exc):
    from fastapi.responses import JSONResponse
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)