# Design Document: Enhanced Detection System

## Overview

The Enhanced Detection System redesigns the AgriCare AI crop disease detection interface with a professional two-column medical-report layout, adds crop pre-selection capability, implements dual AI detection paths (PyTorch for 14 known crops + Gemini Vision AI for unknown crops), and provides comprehensive PDF treatment reports. The enhancement maintains the existing 99%+ accurate PyTorch EfficientNet-B0 model while adding fallback AI detection for crops outside the supported types.

### Goals
- Modernize UI to medical-report style with clean two-column layout (input | results)
- Enable farmers to pre-select crop type before image upload
- Route known crops to PyTorch, unknown crops to Gemini Vision AI
- Provide detailed treatment reports with 4 structured sections
- Generate downloadable PDF reports from detection results and history
- Ensure mobile responsiveness with offline mode for known crops

### Non-Goals
- Real-time video-based detection
- Multi-image batch processing
- Plant species identification beyond disease detection
- Treatment product e-commerce integration
- Multi-language translation beyond Hindi bilingual display

## Architecture

### High-Level Architecture

The system follows a client-server architecture with three primary data flows:

1. **Known Crop Flow**: User → Crop Selector → Flask Backend → PyTorch Model → Enhanced Treatment Display → Optional PDF Generation
2. **Unknown Crop Flow**: User → Crop Selector ("Other/Unknown") → Flask Backend → Gemini Vision API → Enhanced Treatment Display → Optional PDF Generation
3. **PDF Generation Flow**: Detection Results/History → Backend PDF Generator → Downloadable PDF File

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  ┌─────────────────┐           ┌──────────────────────┐        │
│  │  Two-Column UI  │           │  Crop Dropdown       │        │
│  │  (detect.html)  │◄──────────│  Selector Component  │        │
│  └────────┬────────┘           └──────────────────────┘        │
│           │                                                      │
│           │ AJAX                                                 │
│           ▼                                                      │
│  ┌─────────────────┐           ┌──────────────────────┐        │
│  │ JavaScript       │           │  PDF Download        │        │
│  │ Detection Logic  │◄──────────│  Button Component    │        │
│  └─────────────────┘           └──────────────────────┘        │
└───────────┬──────────────────────────────────────────────────────┘
            │
            │ HTTP POST /api/detect-with-crop
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND (Flask)                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │             NEW: /api/detect-with-crop Route                ││
│  │  • Receives: image + crop_selected                          ││
│  │  • Routes to PyTorch OR Gemini based on selection           ││
│  └────────────┬────────────────────────────────────────────────┘│
│               │                                                  │
│    ┌──────────┴───────────┐                                    │
│    │                      │                                    │
│    ▼                      ▼                                    │
│  ┌──────────────┐   ┌────────────────┐                        │
│  │  PyTorch     │   │  NEW: Gemini   │                        │
│  │  Detector    │   │  AI Module     │                        │
│  │ (existing)   │   │ (gemini_ai.py) │                        │
│  └──────┬───────┘   └────────┬───────┘                        │
│         │                    │                                 │
│         └──────────┬─────────┘                                 │
│                    ▼                                            │
│        ┌────────────────────────┐                              │
│        │  Enhanced Treatment    │                              │
│        │  Report Builder        │                              │
│        └──────────┬─────────────┘                              │
│                   │                                             │
│         ┌─────────┴──────────┐                                 │
│         │                    │                                 │
│         ▼                    ▼                                 │
│   ┌──────────┐       ┌────────────────┐                       │
│   │ Database │       │ NEW: PDF       │                       │
│   │ Storage  │       │ Generator      │                       │
│   └──────────┘       └────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
