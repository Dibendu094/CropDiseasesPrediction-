# Requirements Document

## Introduction

This document specifies requirements for enhancing the AgriCare AI Crop Disease Detection system with a redesigned two-column UI, crop pre-selection capability, dual AI detection paths (PyTorch for known crops, Gemini Vision AI for unknown crops), comprehensive PDF treatment reports, and enhanced treatment plan details. The enhancement preserves the existing 99%+ accurate PyTorch EfficientNet-B0 model while adding fallback AI detection for crops outside the 14 supported types.

## Glossary

- **Detection_UI**: The web interface where users upload crop images and view disease diagnosis
- **Crop_Selector**: A dropdown component allowing users to pre-select their crop type before upload
- **PyTorch_Detector**: The existing EfficientNet-B0 model trained on 42 disease classes across 14 crops
- **Gemini_Detector**: Google's Gemini Vision AI used to identify and diagnose unknown crops
- **Treatment_Report**: A comprehensive document containing diagnosis, symptoms, organic remedies, chemical treatments, and prevention tips
- **PDF_Generator**: A system component that creates downloadable PDF reports from treatment plans
- **Detection_Metadata**: Stored information about each scan including crop, disease, confidence, timestamp, and detection source
- **History_Service**: The backend service managing per-user detection history storage and retrieval
- **Known_Crop**: One of the 14 crops supported by the PyTorch model: Apple, Blueberry, Cherry, Corn, Grape, Orange, Peach, Pepper, Potato, Raspberry, Rice, Soybean, Squash, Strawberry, Tomato
- **Unknown_Crop**: Any crop not in the Known_Crop list, requiring Gemini AI detection
- **Detection_Source**: The AI service used for detection (either "PyTorch Model" or "Gemini Vision AI")
- **Bilingual_Display**: Text presentation showing English name with Hindi translation in parentheses

## Requirements

### Requirement 1: Two-Column UI Layout Redesign

**User Story:** As a farmer, I want a clean medical-report style interface with separate input and results sections, so that I can easily follow the diagnosis workflow.

#### Acceptance Criteria

1. WHEN the detect page loads, THE Detection_UI SHALL display a two-column layout on desktop screens (≥992px width)
2. THE Detection_UI SHALL render the left column containing the crop selector and image upload controls
3. THE Detection_UI SHALL render the right column containing an empty state until detection completes
4. THE Detection_UI SHALL apply independent scrollbars to each column on desktop to prevent layout conflicts
5. WHEN the viewport width is <992px, THE Detection_UI SHALL stack columns vertically with single-page scrolling
6. THE Detection_UI SHALL use a clean professional design with minimal borders and Material Design green (#4CAF50) accent colors
7. THE Detection_UI SHALL maintain accessibility with ARIA labels and keyboard navigation support

### Requirement 2: Crop Dropdown Selector

**User Story:** As a farmer, I want to select my crop type before uploading, so that the system knows which AI model to use and can show me relevant information.

#### Acceptance Criteria

1. THE Crop_Selector SHALL display a dropdown with 15 options: 14 Known_Crops plus "Other / Unknown Crop"
2. THE Crop_Selector SHALL render each crop name in Bilingual_Display format (English with Hindi in parentheses)
3. THE Crop_Selector SHALL order Known_Crops alphabetically with "Other / Unknown Crop" appearing last
4. WHEN a user selects a Known_Crop, THE Crop_Selector SHALL mark that selection for PyTorch_Detector routing
5. WHEN a user selects "Other / Unknown Crop", THE Crop_Selector SHALL mark that selection for Gemini_Detector routing
6. THE Crop_Selector SHALL validate that a crop is selected before enabling the detect button
7. THE Crop_Selector SHALL persist the selected crop value across page interactions until detection completes

**Bilingual crop names:**
- Apple (सेब)
- Blueberry (ब्लूबेरी)
- Cherry (चेरी)
- Corn (मक्का)
- Grape (अंगूर)
- Orange (संतरा)
- Peach (आड़ू)
- Pepper (मिर्च)
- Potato (आलू)
- Raspberry (रसभरी)
- Rice (चावल)
- Soybean (सोयाबीन)
- Squash (कद्दू)
- Strawberry (स्ट्रॉबेरी)
- Tomato (टमाटर)
- Other / Unknown Crop (अन्य / अज्ञात फसल)

### Requirement 3: Dual AI Detection Path

**User Story:** As a farmer with a crop not in the 14 supported types, I want the system to still identify my crop and disease using AI, so that I can get treatment recommendations.

#### Acceptance Criteria

1. WHEN a user selects a Known_Crop, THE PyTorch_Detector SHALL process the uploaded image using the existing EfficientNet-B0 model
2. WHEN a user selects "Other / Unknown Crop", THE Gemini_Detector SHALL process the uploaded image using Gemini Vision API
3. THE Gemini_Detector SHALL send the image with a prompt requesting crop identification, disease identification, confidence score, and treatment recommendations
4. THE Gemini_Detector SHALL parse the API response into the same structured format as PyTorch_Detector results
5. THE Detection_UI SHALL display the Detection_Source ("PyTorch Model" or "Gemini Vision AI") in the diagnosis summary
6. WHEN Gemini_Detector is used, THE Treatment_Report SHALL include a disclaimer: "AI-generated recommendations. Consult local agricultural experts for validation."
7. THE system SHALL maintain ≥99% accuracy for Known_Crops using PyTorch_Detector
8. THE system SHALL return results from Gemini_Detector within 5 seconds on average

### Requirement 4: Gemini AI Integration Module

**User Story:** As a system administrator, I want Gemini AI credentials stored securely, so that the fallback detection path works without exposing API keys.

#### Acceptance Criteria

1. THE system SHALL store the Gemini API key in the .env file as GEMINI_API_KEY
2. THE system SHALL create a gemini_ai.py module containing all Gemini Vision API interaction logic
3. THE gemini_ai.py module SHALL export a detect_unknown_crop(image_path: str) function returning detection results
4. THE gemini_ai.py module SHALL handle API errors gracefully, returning user-friendly error messages
5. WHEN the Gemini API is unavailable, THE system SHALL return an error message: "Gemini AI service temporarily unavailable. Please try again later."
6. THE gemini_ai.py module SHALL log all API calls with timestamps for debugging purposes
7. THE gemini_ai.py module SHALL validate image format and size before sending to Gemini API

### Requirement 5: Enhanced Treatment Report Structure

**User Story:** As a farmer, I want detailed treatment plans with clear sections for symptoms, remedies, chemicals, and prevention, so that I can easily understand and apply the recommendations.

#### Acceptance Criteria

1. THE Treatment_Report SHALL display the crop name, disease name, confidence score, and Detection_Source at the top
2. THE Treatment_Report SHALL organize treatment information into four structured sections with emoji icons
3. THE Treatment_Report SHALL render a "🔍 Key Symptoms" section with bullet-pointed symptom descriptions
4. THE Treatment_Report SHALL render a "🌱 Organic Remedy" section with farmer-friendly organic treatment text
5. THE Treatment_Report SHALL render a "🧪 Chemical Spray" section listing specific products, dosages, application methods, and safety warnings
6. THE Treatment_Report SHALL render a "🛡️ Preventive Measures" section with practical prevention tips
7. THE Treatment_Report SHALL use simple language understandable by farmers with basic literacy

### Requirement 6: Disease Information Enhancement

**User Story:** As a farmer, I want detailed treatment explanations in plain language, so that I can understand and apply the recommendations without technical background.

#### Acceptance Criteria

1. THE system SHALL expand the existing disease_info.json file with more detailed farmer-friendly descriptions
2. WHEN disease_info.json contains treatment entries, THE Treatment_Report SHALL display dosage amounts, timing, and application methods
3. THE Treatment_Report SHALL include regional crop names in Hindi and local languages where available
4. THE Treatment_Report SHALL provide practical implementation tips farmers can execute without specialized equipment
5. WHEN a disease has multiple treatment options, THE Treatment_Report SHALL prioritize organic remedies before chemical treatments
6. THE Treatment_Report SHALL display safety warnings prominently for chemical treatments
7. THE system SHALL validate that all disease entries in disease_info.json follow the enhanced format before deployment

### Requirement 7: PDF Download Feature

**User Story:** As a farmer, I want to download my diagnosis report as a PDF, so that I can save it for reference, share with experts, or print for offline use.

#### Acceptance Criteria

1. WHEN detection completes successfully, THE PDF_Generator SHALL render a "Download PDF Report" button at the bottom of the treatment panel
2. WHEN a user clicks the download button, THE PDF_Generator SHALL generate a PDF document within 2 seconds
3. THE PDF_Generator SHALL include the AgriCare logo, uploaded crop image thumbnail, diagnosis summary, and full treatment plan
4. THE PDF_Generator SHALL format the PDF in professional medical-report style with clear sections and readable fonts
5. THE PDF_Generator SHALL name the file using the pattern: "AgriCare_[CropName]_[Date].pdf" (e.g., "AgriCare_Tomato_2025-06-15.pdf")
6. THE PDF_Generator SHALL support mobile browsers with proper download handling for iOS and Android
7. THE PDF_Generator SHALL include a footer with generation timestamp and "Powered by AgriCare AI" branding

### Requirement 8: PDF Download from History

**User Story:** As a signed-in farmer, I want to re-download PDF reports from my history, so that I can access past diagnoses without re-uploading images.

#### Acceptance Criteria

1. WHEN a user views their history page, THE Detection_UI SHALL display a "Download PDF" button next to each history entry
2. WHEN a user clicks a history PDF button, THE PDF_Generator SHALL recreate the PDF from stored Detection_Metadata
3. THE History_Service SHALL store all Detection_Metadata required for PDF regeneration including crop, disease, confidence, symptoms, treatment, and timestamp
4. THE PDF_Generator SHALL generate historical PDFs with the same format and quality as fresh detection PDFs
5. WHEN Detection_Metadata is incomplete, THE PDF_Generator SHALL display a message: "PDF unavailable for this scan. Metadata incomplete."
6. THE system SHALL allow unlimited PDF downloads for signed-in users from their history
7. THE system SHALL include the original detection date in historical PDF filenames

### Requirement 9: Async Gemini API Processing

**User Story:** As a user, I want the UI to remain responsive during Gemini AI processing, so that I know the system is working and don't experience browser freezing.

#### Acceptance Criteria

1. WHEN Gemini_Detector is processing, THE Detection_UI SHALL display an animated loading overlay with progress indicator
2. THE Detection_UI SHALL remain interactive during Gemini API calls, allowing users to cancel the operation
3. WHEN Gemini API response takes >3 seconds, THE Detection_UI SHALL display a message: "Analyzing unknown crop... this may take a moment"
4. THE system SHALL implement async/await patterns for all Gemini API calls to prevent blocking
5. WHEN a user cancels during Gemini processing, THE system SHALL abort the API request and reset the UI to initial state
6. THE system SHALL implement a 15-second timeout for Gemini API calls, returning an error if exceeded
7. THE Detection_UI SHALL provide visual feedback (spinner, progress bar) during all async operations

### Requirement 10: Offline Mode for Known Crops

**User Story:** As a farmer in an area with unstable internet, I want the system to work offline for known crops, so that I can get diagnoses even without continuous connectivity.

#### Acceptance Criteria

1. WHEN a user selects a Known_Crop and uploads an image, THE PyTorch_Detector SHALL process the image entirely client-side or server-side without external API calls
2. THE system SHALL NOT require internet connectivity after page load for PyTorch_Detector processing
3. WHEN a user attempts to use Gemini_Detector offline, THE Detection_UI SHALL display a message: "Internet connection required for unknown crop detection"
4. THE system SHALL cache the PyTorch model and disease_info.json for offline availability
5. THE PDF_Generator SHALL function offline for PyTorch_Detector results
6. WHEN a user is offline, THE Detection_UI SHALL disable the "Other / Unknown Crop" option in Crop_Selector
7. THE system SHALL detect network status and provide appropriate UI feedback for offline/online state

### Requirement 11: Mobile-Responsive Design

**User Story:** As a farmer using a mobile phone, I want the UI to work smoothly on small screens, so that I can use the system from the field.

#### Acceptance Criteria

1. WHEN the viewport width is <768px, THE Detection_UI SHALL stack the two-column layout into a single vertical column
2. THE Crop_Selector SHALL render as a native mobile select dropdown on touchscreen devices
3. THE PDF_Generator SHALL trigger native download/share dialogs on mobile browsers
4. THE Detection_UI SHALL use touch-friendly button sizes (minimum 44×44px) on mobile devices
5. WHEN a user uploads an image on mobile, THE Detection_UI SHALL allow image capture from camera or photo library
6. THE Treatment_Report SHALL use readable font sizes (≥16px) on mobile to prevent zoom requirements
7. THE system SHALL maintain full functionality across iOS Safari, Chrome Mobile, and Android Chrome browsers

### Requirement 12: Treatment Plan Expansion

**User Story:** As a farmer, I want comprehensive treatment plans with local product names, so that I can purchase and apply the correct treatments from nearby agricultural stores.

#### Acceptance Criteria

1. THE system SHALL expand disease_info.json with at least 3 treatment options per disease
2. WHEN a disease has chemical treatments, THE Treatment_Report SHALL list product names commonly available in India
3. THE Treatment_Report SHALL include dosage measurements in both metric (grams/liter) and traditional farmer units where applicable
4. THE Treatment_Report SHALL specify application timing (e.g., "spray at first sign of disease" or "apply 7 days before harvest")
5. THE Treatment_Report SHALL include safety precautions for each chemical treatment (PPE requirements, harvest intervals)
6. WHEN organic remedies are available, THE Treatment_Report SHALL prioritize them and explain their preparation from commonly available materials
7. THE system SHALL validate that all treatment entries include: name, purpose, dosage, interval, and safety information

### Requirement 13: Detection History Metadata Storage

**User Story:** As a signed-in farmer, I want my scan history to include all diagnosis details, so that I can review past results and re-download reports.

#### Acceptance Criteria

1. WHEN a signed-in user completes a detection, THE History_Service SHALL store Detection_Metadata including crop, disease, confidence, Detection_Source, symptoms, treatment, prevention, and timestamp
2. THE History_Service SHALL store the uploaded image path for display in history thumbnails
3. THE History_Service SHALL store Detection_Metadata in the user's private PostgreSQL schema
4. WHEN a user views history, THE Detection_UI SHALL display entries with thumbnail, crop, disease, date, and confidence score
5. THE History_Service SHALL support retrieval of Detection_Metadata by detection ID for PDF regeneration
6. THE system SHALL limit history storage to 50 most recent scans per user to manage database size
7. WHEN a user deletes a history entry, THE History_Service SHALL remove the Detection_Metadata and associated image file

### Requirement 14: Confidence Score Display

**User Story:** As a farmer, I want to see how confident the AI is in its diagnosis, so that I can decide whether to consult additional experts.

#### Acceptance Criteria

1. WHEN detection completes, THE Treatment_Report SHALL display the confidence score as a percentage (0-100%)
2. THE Detection_UI SHALL render a visual confidence bar colored green (≥90%), yellow (70-89%), or red (<70%)
3. THE Detection_UI SHALL display a confidence badge with text "High" (≥90%), "Medium" (70-89%), or "Low" (<70%)
4. WHEN confidence is below 70%, THE Treatment_Report SHALL include a warning: "Low confidence. Consider consulting a local agricultural expert."
5. THE system SHALL calculate confidence from PyTorch_Detector softmax output or Gemini_Detector API response
6. THE PDF_Generator SHALL include the confidence score and level in the generated report
7. THE Treatment_Report SHALL display the Detection_Source next to the confidence score

### Requirement 15: Gemini Prompt Engineering

**User Story:** As a system developer, I want well-crafted Gemini prompts, so that the AI returns accurate and structured crop disease information.

#### Acceptance Criteria

1. THE Gemini_Detector SHALL use a prompt requesting: crop type, disease name, confidence level, symptoms, organic treatments, chemical treatments, prevention tips
2. THE Gemini_Detector SHALL instruct the AI to format responses as JSON for reliable parsing
3. THE Gemini_Detector SHALL include example output format in the prompt to guide AI responses
4. WHEN Gemini returns unstructured text, THE Gemini_Detector SHALL attempt to parse key-value pairs using regex patterns
5. THE Gemini_Detector SHALL validate that parsed responses contain required fields before returning results
6. WHEN Gemini fails to identify the crop, THE Gemini_Detector SHALL return an error: "Unable to identify crop. Please ensure the image shows clear leaf features."
7. THE system SHALL log all Gemini prompts and responses for quality improvement and debugging

### Requirement 16: Error Handling for Unknown Crops

**User Story:** As a user, I want clear error messages when Gemini AI cannot identify my crop, so that I understand what went wrong and can retry with a better image.

#### Acceptance Criteria

1. WHEN Gemini_Detector fails to identify a crop, THE Detection_UI SHALL display: "Unable to identify crop from image. Try uploading a clearer photo of the leaves."
2. WHEN Gemini API returns an error, THE Detection_UI SHALL display: "Detection service temporarily unavailable. Please try again in a few moments."
3. WHEN Gemini API rate limit is exceeded, THE Detection_UI SHALL display: "Too many requests. Please wait a moment and try again."
4. THE system SHALL log all Gemini errors with timestamps and error codes for administrator review
5. WHEN an error occurs, THE Detection_UI SHALL allow users to retry immediately without reloading the page
6. THE Detection_UI SHALL provide a "Report Problem" link for users to submit feedback on failed detections
7. THE system SHALL track Gemini error rates and alert administrators when error rate exceeds 10%

### Requirement 17: Bilingual Support Foundation

**User Story:** As a Hindi-speaking farmer, I want crop names displayed in Hindi, so that I can recognize them easily.

#### Acceptance Criteria

1. THE Crop_Selector SHALL display all crop names in Bilingual_Display format with Hindi translations
2. THE Treatment_Report SHALL display crop names and disease names in English with Hindi translations in parentheses
3. THE system SHALL store Hindi translations in a translations.json file for maintainability
4. WHEN a Hindi translation is missing, THE Detection_UI SHALL display the English name without parentheses
5. THE PDF_Generator SHALL include Hindi crop names in generated reports
6. THE system SHALL validate that all 14 Known_Crops have Hindi translations before deployment
7. THE system SHALL provide a framework for adding additional regional languages in future updates

### Requirement 18: Performance Optimization

**User Story:** As a user, I want fast detection results, so that I don't waste time waiting for diagnoses.

#### Acceptance Criteria

1. WHEN a user uploads an image for a Known_Crop, THE PyTorch_Detector SHALL return results within 2 seconds
2. WHEN a user uploads an image for an Unknown_Crop, THE Gemini_Detector SHALL return results within 5 seconds on average
3. THE PDF_Generator SHALL generate PDFs within 2 seconds of user request
4. THE Detection_UI SHALL load the detect page within 1 second on 4G connections
5. THE system SHALL compress uploaded images to <2MB before processing to optimize network transfer
6. THE system SHALL cache the PyTorch model in memory to avoid reload overhead
7. THE system SHALL implement lazy loading for treatment report sections to improve perceived performance

### Requirement 19: Accessibility Compliance

**User Story:** As a user with disabilities, I want the detection UI to be accessible via screen readers and keyboard navigation, so that I can use the system independently.

#### Acceptance Criteria

1. THE Detection_UI SHALL provide ARIA labels for all interactive elements (buttons, dropdowns, file inputs)
2. THE Detection_UI SHALL support full keyboard navigation with visible focus indicators
3. THE Crop_Selector SHALL announce selected crop to screen readers
4. THE Treatment_Report SHALL use semantic HTML heading hierarchy (h1 → h2 → h3) for section structure
5. THE PDF_Generator SHALL generate accessible PDFs with proper heading tags and alt text for images
6. THE Detection_UI SHALL maintain color contrast ratios of at least 4.5:1 for normal text and 3:1 for large text
7. THE system SHALL pass WCAG 2.1 Level AA automated accessibility tests

### Requirement 20: Database Schema for Enhanced Metadata

**User Story:** As a system administrator, I want the database to store all detection metadata efficiently, so that users can retrieve full history with PDF regeneration capability.

#### Acceptance Criteria

1. THE History_Service SHALL extend the detection history table schema to include columns: crop_selected, detection_source, symptoms_json, treatment_json, prevention_json, fertilizers_json
2. THE History_Service SHALL store the crop_selected value from Crop_Selector for routing verification
3. THE History_Service SHALL serialize complex treatment data as JSON for flexible storage
4. THE History_Service SHALL index the detection_id, user_id, and created_at columns for fast queries
5. WHEN a user queries their history, THE History_Service SHALL return results ordered by created_at descending
6. THE History_Service SHALL implement database migration scripts to upgrade existing schemas without data loss
7. THE system SHALL validate that all Detection_Metadata fields are non-null before saving to prevent incomplete records
