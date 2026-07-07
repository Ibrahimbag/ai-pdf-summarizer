// ==========================================================================
// Summarix AI - Frontend Application Controller
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
    // State Variables
    let selectedFile = null;
    let selectedTone = "simple";
    let analysisResult = null;

    // DOM Elements
    const settingsToggleBtn = document.getElementById("settingsToggleBtn");
    const settingsPanel = document.getElementById("settingsPanel");
    const providerSelect = document.getElementById("providerSelect");
    const apiKeyInput = document.getElementById("apiKeyInput");
    const togglePasswordBtn = document.getElementById("togglePasswordBtn");
    const saveSettingsBtn = document.getElementById("saveSettingsBtn");
    
    const toneSelector = document.getElementById("toneSelector");
    const tonePills = document.querySelectorAll(".tone-pill");
    
    const pdfDropzone = document.getElementById("pdfDropzone");
    const pdfFileInput = document.getElementById("pdfFileInput");
    const fileInfoContainer = document.getElementById("fileInfoContainer");
    const selectedFileName = document.getElementById("selectedFileName");
    const selectedFileSize = document.getElementById("selectedFileSize");
    const clearFileBtn = document.getElementById("clearFileBtn");
    const processBtn = document.getElementById("processBtn");
    
    const progressCard = document.getElementById("progressCard");
    const chunksStepLabel = document.getElementById("chunksStepLabel");
    const stepParsing = document.getElementById("step-parsing");
    const stepChunks = document.getElementById("step-chunks");
    const stepActions = document.getElementById("step-actions");
    
    const emptyState = document.getElementById("emptyState");
    const resultsContainer = document.getElementById("resultsContainer");
    const summaryTextOutput = document.getElementById("summaryTextOutput");
    const bulletsOutputList = document.getElementById("bulletsOutputList");
    const actionItemsCount = document.getElementById("actionItemsCount");
    const actionsTable = document.getElementById("actionsTable");
    const actionsTableBody = document.getElementById("actionsTableBody");
    const noActionsFallback = document.getElementById("noActionsFallback");
    
    const copyJsonBtn = document.getElementById("copyJsonBtn");
    const downloadJsonBtn = document.getElementById("downloadJsonBtn");
    
    const toast = document.getElementById("toast");
    const toastMessage = document.getElementById("toastMessage");

    // ==========================================================================
    // Initialization & Settings Configuration
    // ==========================================================================
    
    // Load saved settings from LocalStorage
    function loadSettings() {
        const provider = localStorage.getItem("summarix_provider");
        const apiKey = localStorage.getItem("summarix_api_key");
        
        if (provider) {
            providerSelect.value = provider;
        }
        if (apiKey) {
            apiKeyInput.value = apiKey;
        } else {
            // Open settings panel by default if API key is missing
            settingsPanel.style.display = "block";
            showToast("Configure your API settings to start summarizing PDFs.");
        }
    }
    
    loadSettings();

    // Toggle Settings panel visibility
    settingsToggleBtn.addEventListener("click", () => {
        if (settingsPanel.style.display === "none" || !settingsPanel.style.display) {
            settingsPanel.style.display = "block";
            settingsPanel.scrollIntoView({ behavior: "smooth" });
        } else {
            settingsPanel.style.display = "none";
        }
    });

    // Toggle Password Visibility
    togglePasswordBtn.addEventListener("click", () => {
        const type = apiKeyInput.type === "password" ? "text" : "password";
        apiKeyInput.type = type;
        const icon = togglePasswordBtn.querySelector("i");
        if (type === "text") {
            icon.classList.remove("fa-eye");
            icon.classList.add("fa-eye-slash");
        } else {
            icon.classList.remove("fa-eye-slash");
            icon.classList.add("fa-eye");
        }
    });

    // Save Settings
    saveSettingsBtn.addEventListener("click", () => {
        const provider = providerSelect.value;
        const apiKey = apiKeyInput.value.trim();
        
        localStorage.setItem("summarix_provider", provider);
        localStorage.setItem("summarix_api_key", apiKey);
        
        showToast("API configuration saved successfully!");
        
        // Hide panel if key is entered
        if (apiKey) {
            setTimeout(() => {
                settingsPanel.style.display = "none";
            }, 800);
        }
    });

    // Helper: Show Toast Notification
    function showToast(message) {
        toastMessage.textContent = message;
        toast.classList.add("show");
        setTimeout(() => {
            toast.classList.remove("show");
        }, 3000);
    }

    // ==========================================================================
    // Tone Selection Handling
    // ==========================================================================
    tonePills.forEach(pill => {
        pill.addEventListener("click", () => {
            tonePills.forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            selectedTone = pill.getAttribute("data-tone");
        });
    });

    // ==========================================================================
    // File Upload Handling (Drag-and-Drop)
    // ==========================================================================
    
    // Browse button link trigger
    pdfDropzone.addEventListener("click", (e) => {
        if (e.target.closest("#clearFileBtn") || e.target.closest(".file-info-container")) {
            return; // Don't trigger browse if clearing file or clicking details
        }
        pdfFileInput.click();
    });

    pdfFileInput.addEventListener("change", (e) => {
        handleFiles(e.target.files);
    });

    // Drag events
    ["dragenter", "dragover"].forEach(eventName => {
        pdfDropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            pdfDropzone.classList.add("dragover");
        }, false);
    });

    ["dragleave", "drop"].forEach(eventName => {
        pdfDropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            pdfDropzone.classList.remove("dragover");
        }, false);
    });

    pdfDropzone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    // Process Selected Files
    function handleFiles(files) {
        if (files.length === 0) return;
        
        const file = files[0];
        
        // Validate is PDF
        if (file.type !== "application/pdf" && !file.name.toLowerCase().endswith(".pdf")) {
            showToast("Invalid file format. Only PDF documents are allowed.");
            return;
        }
        
        // Validate Size (max 10MB)
        const maxSize = 10 * 1024 * 1024;
        if (file.size > maxSize) {
            showToast("File size too large. Maximum size is 10MB.");
            return;
        }
        
        selectedFile = file;
        
        // Show file details in UI
        selectedFileName.textContent = file.name;
        selectedFileSize.textContent = formatBytes(file.size);
        
        // Hide upload content, show file details content
        pdfDropzone.querySelector(".dropzone-content").style.display = "none";
        fileInfoContainer.style.display = "flex";
        
        // Enable Process Button
        processBtn.classList.remove("disabled");
    }

    // Clear Selected File
    clearFileBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        selectedFile = null;
        pdfFileInput.value = "";
        
        // Restore upload content, hide file details
        pdfDropzone.querySelector(".dropzone-content").style.display = "flex";
        fileInfoContainer.style.display = "none";
        
        // Disable Process Button
        processBtn.classList.add("disabled");
    });

    // Format byte sizes nicely
    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return "0 Bytes";
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ["Bytes", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
    }

    // ==========================================================================
    // API Call & Processing Workflow
    // ==========================================================================
    processBtn.addEventListener("click", async () => {
        if (!selectedFile) return;

        const provider = providerSelect.value;
        const apiKey = apiKeyInput.value.trim();

        // Let server handle key validation too, but we can do a sanity check here
        if (!apiKey) {
            settingsPanel.style.display = "block";
            settingsPanel.scrollIntoView({ behavior: "smooth" });
            showToast("Please save your API key in the settings panel first.");
            return;
        }

        // 1. Reset UI States
        emptyState.style.display = "none";
        resultsContainer.style.display = "none";
        progressCard.style.display = "block";
        processBtn.classList.add("disabled");
        processBtn.innerHTML = `<span>Processing...</span> <i class="fa-solid fa-circle-notch fa-spin"></i>`;
        
        setStepState(stepParsing, "active");
        setStepState(stepChunks, "inactive");
        setStepState(stepActions, "inactive");
        
        // 2. Prepare FormData
        const formData = new FormData();
        formData.append("file", selectedFile);
        formData.append("tone", selectedTone);
        formData.append("provider", provider);
        formData.append("api_key", apiKey);

        try {
            // Mock progression transitions for a smoother UX
            // Since FastAPI processes everything in one endpoint, we simulate steps
            // Step 1: Parsing PDF (instant upload & local extraction)
            // Let's hold parsing active for a bit, then move to Chunking
            setTimeout(() => {
                setStepState(stepParsing, "completed");
                setStepState(stepChunks, "active");
            }, 1500);

            // Step 2: Summarizing chunks
            // Set a timer to check progress or just animate a bit while we wait
            const chunkInterval = setInterval(() => {
                if (stepChunks.classList.contains("active")) {
                    // Just a visual micro-animation/text update
                    const label = chunksStepLabel.textContent;
                    if (!label.includes("...")) {
                        chunksStepLabel.textContent = label + "...";
                    }
                }
            }, 1000);

            // Trigger Backend call
            const response = await fetch("/api/summarize", {
                method: "POST",
                body: formData
            });

            clearInterval(chunkInterval);

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Server failed to process the document.");
            }

            analysisResult = await response.json();
            
            // Advance steps immediately to completion on success
            setStepState(stepChunks, "completed");
            setStepState(stepActions, "active");
            
            setTimeout(() => {
                setStepState(stepActions, "completed");
                displayResults(analysisResult);
                
                // Show success view
                progressCard.style.display = "none";
                resultsContainer.style.display = "block";
                resultsContainer.scrollIntoView({ behavior: "smooth" });
                
                showToast("Document analyzed successfully!");
            }, 800);

        } catch (error) {
            console.error("Error summarizing document:", error);
            showToast(error.message || "An error occurred while processing the PDF.");
            
            // Reset state back to upload screen
            progressCard.style.display = "none";
            emptyState.style.display = "flex";
        } finally {
            // Restore process button state
            processBtn.classList.remove("disabled");
            processBtn.innerHTML = `<span>Summarize PDF</span> <i class="fa-solid fa-bolt"></i>`;
        }
    });

    // Helper: Update step item state classes
    function setStepState(element, state) {
        element.classList.remove("active", "completed");
        
        const bulletIcon = element.querySelector(".step-bullet i");
        bulletIcon.className = ""; // clear classes
        
        if (state === "active") {
            element.classList.add("active");
            bulletIcon.className = "fa-solid fa-circle-notch fa-spin";
        } else if (state === "completed") {
            element.classList.add("completed");
            bulletIcon.className = "fa-solid fa-circle-check";
        } else {
            bulletIcon.className = "fa-solid fa-circle";
        }
    }

    // ==========================================================================
    // Render Results to UI
    // ==========================================================================
    function displayResults(data) {
        // 1. Set summary paragraph
        summaryTextOutput.textContent = data.summary || "No overall summary generated.";
        
        // 2. Set bullet points
        bulletsOutputList.innerHTML = "";
        if (data.bullet_points && data.bullet_points.length > 0) {
            data.bullet_points.forEach(bullet => {
                const li = document.createElement("li");
                li.textContent = bullet;
                bulletsOutputList.appendChild(li);
            });
        } else {
            bulletsOutputList.innerHTML = "<li>No takeaways generated.</li>";
        }
        
        // 3. Render action items table
        actionsTableBody.innerHTML = "";
        const actions = data.actions || [];
        
        actionItemsCount.textContent = `${actions.length} Item${actions.length !== 1 ? 's' : ''}`;
        
        if (actions.length > 0) {
            actionsTable.style.display = "table";
            noActionsFallback.style.display = "none";
            
            actions.forEach(item => {
                const tr = document.createElement("tr");
                
                // Task column
                const tdTask = document.createElement("td");
                tdTask.className = "td-task";
                tdTask.textContent = item.task || "Unspecified task";
                tr.appendChild(tdTask);
                
                // Responsible column
                const tdResp = document.createElement("td");
                if (item.responsible) {
                    const initials = getInitials(item.responsible);
                    tdResp.innerHTML = `
                        <div class="responsible-tag">
                            <div class="responsible-avatar">${initials}</div>
                            <span>${item.responsible}</span>
                        </div>
                    `;
                } else {
                    tdResp.innerHTML = `<span class="responsible-null">—</span>`;
                }
                tr.appendChild(tdResp);
                
                // Deadline column
                const tdDeadline = document.createElement("td");
                if (item.deadline) {
                    tdDeadline.innerHTML = `
                        <div class="deadline-badge">
                            <i class="fa-regular fa-clock"></i>
                            <span>${item.deadline}</span>
                        </div>
                    `;
                } else {
                    tdDeadline.innerHTML = `<span class="deadline-null">—</span>`;
                }
                tr.appendChild(tdDeadline);
                
                actionsTableBody.appendChild(tr);
            });
        } else {
            actionsTable.style.display = "none";
            noActionsFallback.style.display = "flex";
        }
    }

    // Helper: Get user initials for avatar
    function getInitials(name) {
        if (!name) return "?";
        const parts = name.split(" ");
        if (parts.length >= 2) {
            return (parts[0][0] + parts[1][0]).toUpperCase();
        }
        return name[0].toUpperCase();
    }

    // ==========================================================================
    // Clipboard & Export Utilities
    // ==========================================================================
    
    // Copy JSON to Clipboard
    copyJsonBtn.addEventListener("click", () => {
        if (!analysisResult) return;
        
        const jsonStr = JSON.stringify(analysisResult, null, 2);
        
        navigator.clipboard.writeText(jsonStr).then(() => {
            showToast("JSON copied to clipboard!");
            
            // Temporary button label animation
            const originalHTML = copyJsonBtn.innerHTML;
            copyJsonBtn.innerHTML = `<i class="fa-solid fa-check" style="color: var(--accent-green)"></i> Copied!`;
            setTimeout(() => {
                copyJsonBtn.innerHTML = originalHTML;
            }, 2000);
        }).catch(err => {
            console.error("Clipboard copy error:", err);
            showToast("Failed to copy JSON.");
        });
    });

    // Download JSON file
    downloadJsonBtn.addEventListener("click", () => {
        if (!analysisResult) return;
        
        const jsonStr = JSON.stringify(analysisResult, null, 2);
        const blob = new Blob([jsonStr], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement("a");
        a.href = url;
        
        // Clean original file name for JSON download
        const origName = selectedFile ? selectedFile.name.replace(/\.[^/.]+$/, "") : "document";
        a.download = `${origName}_summary.json`;
        
        document.body.appendChild(a);
        a.click();
        
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showToast("JSON downloaded successfully.");
    });
});
