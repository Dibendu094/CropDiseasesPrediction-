# Implementation Plan: Complete Authentication UI

## Overview

This implementation plan adds prominent Sign Up and Sign In buttons to the home page hero section with conditional rendering based on authentication state. The approach involves minimal template changes with no backend modifications, leveraging existing CSS classes and authentication infrastructure.

## Tasks

- [ ] 1. Add authentication buttons to home page hero section
  - [ ] 1.1 Add Sign Up and Sign In buttons with conditional rendering
    - Modify templates/index.html hero-buttons container
    - Add Jinja2 conditional block `{% if not current_user %}`
    - Insert Sign Up button with btn-primary-green styling
    - Insert Sign In button with btn-outline-green styling
    - Add Bootstrap Icons (bi-person-plus, bi-box-arrow-in-right)
    - Add ARIA labels for accessibility
    - Both buttons link to /auth route
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 4.1, 4.2, 4.3, 6.1, 6.2_
  
  - [ ]* 1.2 Write unit tests for button rendering
    - Test unauthenticated state shows Sign Up and Sign In buttons
    - Test authenticated state hides authentication buttons
    - Test button attributes (href, classes, icons)
    - Test ARIA labels presence
    - _Requirements: 3.1, 3.2, 3.3, 6.1, 6.2_

- [ ] 2. Add password visibility toggle to signin form
  - [ ] 2.1 Add password toggle button to signin password field
    - Modify templates/auth.html signin form
    - Wrap #signinPassword input in password-wrapper div
    - Add btn-show-password button with bi-eye-slash icon
    - Add aria-label "Show password" for accessibility
    - Mirror the structure from signup form password field
    - _Requirements: User request for password view option on signin page_
  
  - [ ] 2.2 Update JavaScript to handle signin password toggle
    - Modify static/js/auth.js
    - Ensure existing password toggle logic applies to signin form
    - Test toggle functionality for signin password field
    - Verify icon switches between bi-eye and bi-eye-slash
    - _Requirements: User request for password view option on signin page_
  
  - [ ]* 2.3 Write unit tests for password toggle
    - Test password field toggles between password and text type
    - Test icon changes on toggle
    - Test ARIA label updates
    - _Requirements: 6.3, 6.4_

- [ ] 3. Checkpoint - Verify template changes and authentication flow
  - Ensure all tests pass, ask the user if questions arise.
  - Manually test authentication flow: home → auth → signup → signin → detect
  - Verify buttons appear/hide based on authentication state
  - Test responsive behavior on mobile viewport

- [ ] 4. Verify responsive layout and accessibility
  - [ ]* 4.1 Test responsive behavior across viewports
    - Test desktop layout (>768px width): buttons in horizontal row
    - Test tablet layout (576-768px): buttons wrap appropriately
    - Test mobile layout (<576px): buttons stack vertically with full width
    - Verify 16px gap between buttons maintained
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [ ]* 4.2 Test accessibility compliance
    - Verify keyboard navigation (tab through buttons)
    - Verify focus states visible
    - Test with screen reader (announce button labels correctly)
    - Verify color contrast meets WCAG AA (4.5:1 minimum)
    - Verify touch target size meets 44x44px minimum on mobile
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [ ] 5. Integration testing and final validation
  - [ ]* 5.1 Write integration tests for authentication flow
    - Test signup flow from home page Sign Up button
    - Test signin flow from home page Sign In button
    - Verify redirect to /detect after successful authentication
    - Verify navbar updates to show user menu after authentication
    - Verify home page hides auth buttons after authentication
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 6. Final checkpoint - Complete flow validation
  - Ensure all tests pass, ask the user if questions arise.
  - Test complete user journey: home → signup → detect → logout → home → signin → detect
  - Verify no console errors in browser
  - Verify responsive behavior on actual mobile device if available

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- No backend changes required - leverages existing Flask routes and context processor
- No new CSS classes needed - reuses existing btn-primary-green and btn-outline-green
- Password toggle functionality already exists in signup form, just needs to be added to signin form
- Checkpoints ensure incremental validation of authentication flow and responsive behavior

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["1.2", "2.2"] },
    { "id": 2, "tasks": ["2.3", "4.1", "4.2"] },
    { "id": 3, "tasks": ["5.1"] }
  ]
}
```
