# Design Document: Complete Authentication UI

## Overview

This design specifies the implementation for adding visible authentication entry points (Sign Up and Sign In buttons) to the hero section of the AgriCare AI home page. The feature enhances user onboarding by making authentication access prominent on the landing page while maintaining design consistency with the existing Material Design green theme.

### Key Design Goals

1. **Discoverability**: Make authentication entry points immediately visible to new visitors on the hero section
2. **Design Consistency**: Match the existing Material Design green theme and button styling patterns
3. **Responsive Layout**: Ensure buttons work gracefully across all viewport sizes
4. **State Awareness**: Hide authentication prompts for already-logged-in users
5. **Accessibility**: Ensure keyboard navigation, ARIA labels, and sufficient color contrast

### Scope

**In Scope:**
- Add Sign Up and Sign In buttons to the home page hero section
- Conditional rendering based on authentication state
- Responsive button layout for mobile and desktop viewports
- Integration with existing /auth route
- Visual styling consistent with Material Design theme
- Accessibility improvements (ARIA labels, focus states, keyboard navigation)

**Out of Scope:**
- Changes to the authentication backend logic (auth.py)
- Modifications to the /auth page UI (auth.html)
- Changes to the navbar authentication controls
- Email verification or social authentication
- Database schema changes
- Password reset flow modifications

## Architecture

### Component Overview

The implementation involves a single frontend template modification with conditional rendering logic. The existing Flask authentication system and routing remain unchanged.

```
┌─────────────────────────────────────────────────────────┐
│                      Home Page (index.html)              │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │            Hero Section                            │ │
│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  │  Title: "Crop Disease Detection"            │  │ │
│  │  │  Subtitle: "Upload a crop leaf image..."    │  │ │
│  │  └──────────────────────────────────────────────┘  │ │
│  │                                                     │ │
│  │  ┌──────────────────────────────────────────────┐  │ │
│  │  │  Hero Buttons Container                      │  │ │
│  │  │                                               │  │ │
│  │  │  {% if not current_user %}                   │  │ │
│  │  │    ┌──────────────┐  ┌──────────────┐       │  │ │
│  │  │    │  Sign Up     │  │  Sign In     │       │  │ │
│  │  │    │ (btn-primary)│  │ (btn-outline)│       │  │ │
│  │  │    └──────────────┘  └──────────────┘       │  │ │
│  │  │  {% endif %}                                 │  │ │
│  │  │                                               │  │ │
│  │  │  ┌──────────────────┐  ┌─────────────────┐  │  │ │
│  │  │  │ Start Detection  │  │ Supported Crops │  │  │ │
│  │  │  └──────────────────┘  └─────────────────┘  │  │ │
│  │  └──────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
                          │ Click Sign Up / Sign In
                          ▼
           ┌──────────────────────────────┐
           │   /auth Route                 │
           │   (auth.html template)        │
           │   - Tabbed signin/signup form │
           │   - Form submission via AJAX  │
           └──────────────────────────────┘
                          │
                          │ Authentication Success
                          ▼
           ┌──────────────────────────────┐
           │   Redirect to /detect        │
           │   - User session established │
           │   - Navbar shows user menu   │
           └──────────────────────────────┘
```

### Authentication Flow

1. **Unauthenticated User Journey:**
   - User lands on home page
   - Sees Sign Up and Sign In buttons in hero section
   - Clicks either button → navigates to /auth
   - Completes authentication → redirects to /detect
   - Navbar updates to show user menu

2. **Authenticated User Journey:**
   - User lands on home page
   - Hero section does NOT show Sign Up/Sign In buttons
   - Sees only "Start Detection" and "Supported Crops" buttons
   - Navbar shows user avatar/menu

### Template Context

The design leverages the existing Flask context processor that provides `current_user` to all templates:

```python
@app.context_processor
def inject_globals():
    return {
        'current_user': current_user(),  # Returns user dict or None
    }
```

## Components and Interfaces

### Template Modifications (index.html)

**Location:** `templates/index.html`, hero section, `.hero-buttons` container

**Current Structure:**
```html
<div class="hero-buttons">
    <a href="/detect" class="btn btn-primary-green btn-lg">
        <i class="bi bi-cloud-upload"></i>
        Start Detection
    </a>
    <a href="#supported-crops" class="btn btn-outline-green btn-lg">
        <i class="bi bi-grid-3x3-gap"></i>
        Supported Crops
    </a>
</div>
```

**New Structure:**
```html
<div class="hero-buttons">
    {% if not current_user %}
    <!-- Authentication buttons (visible only when not logged in) -->
    <a href="/auth" class="btn btn-primary-green btn-lg" aria-label="Sign up for a new account">
        <i class="bi bi-person-plus"></i>
        Sign Up
    </a>
    <a href="/auth" class="btn btn-outline-green btn-lg" aria-label="Sign in to your account">
        <i class="bi bi-box-arrow-in-right"></i>
        Sign In
    </a>
    {% endif %}
    
    <!-- Core action buttons (always visible) -->
    <a href="/detect" class="btn btn-primary-green btn-lg">
        <i class="bi bi-cloud-upload"></i>
        Start Detection
    </a>
    <a href="#supported-crops" class="btn btn-outline-green btn-lg">
        <i class="bi bi-grid-3x3-gap"></i>
        Supported Crops
    </a>
</div>
```

### CSS Styling

**No new CSS classes required.** The design reuses existing button classes:

- `.btn-primary-green` - Green gradient button (for Sign Up)
- `.btn-outline-green` - Outlined green button (for Sign In)
- `.btn-lg` - Large button size
- `.hero-buttons` - Flex container with responsive wrapping

**Existing CSS (no changes needed):**
```css
.hero-buttons {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 48px;
    animation: fadeInUp 0.6s ease-out 0.3s both;
}

.btn-primary-green {
    background: var(--gradient-green);
    border: none;
    color: var(--white);
    padding: 14px 32px;
    border-radius: var(--radius-full);
    font-weight: 600;
    font-size: 1rem;
    display: inline-flex;
    align-items: center;
    gap: 10px;
    box-shadow: var(--shadow-green);
    transition: var(--transition-base);
}

.btn-primary-green:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 32px rgba(76, 175, 80, 0.35);
    color: var(--white);
}

.btn-outline-green {
    background: transparent;
    border: 2px solid var(--green-300);
    color: var(--green-700);
    padding: 12px 30px;
    border-radius: var(--radius-full);
    font-weight: 600;
    font-size: 1rem;
    display: inline-flex;
    align-items: center;
    gap: 10px;
    transition: var(--transition-base);
}

.btn-outline-green:hover {
    background: var(--green-50);
    border-color: var(--green-500);
    color: var(--green-800);
    transform: translateY(-2px);
}
```

**Responsive Behavior (existing CSS):**
```css
@media (max-width: 767.98px) {
    .hero-buttons {
        justify-content: center;
    }
}

@media (max-width: 575.98px) {
    .hero-buttons {
        flex-direction: column;
        align-items: center;
    }

    .btn-primary-green,
    .btn-outline-green {
        width: 100%;
        justify-content: center;
    }
}
```

### Icon Selection

The design uses Bootstrap Icons (already included in the project):

- **Sign Up Button:** `bi-person-plus` (person with plus sign)
- **Sign In Button:** `bi-box-arrow-in-right` (box with arrow entering)

These icons are semantically appropriate and visually distinct from the existing "Start Detection" (`bi-cloud-upload`) and "Supported Crops" (`bi-grid-3x3-gap`) icons.

### Backend Integration

**No backend changes required.** The design leverages existing Flask routes and authentication logic:

1. **Authentication Check:** Uses existing `current_user()` helper injected via `@app.context_processor`
2. **Navigation Target:** Both buttons link to `/auth` route (existing)
3. **Post-Authentication Redirect:** Existing logic in `auth.html` redirects to `/detect` after successful authentication

**Existing Route Structure:**
```python
@app.route('/auth')
def auth_page():
    """Combined sign-in / sign-up page. Redirect to /detect if already logged in."""
    if current_user():
        return redirect(url_for('detect_page'))
    next_url = request.args.get('next', '/detect')
    return render_template('auth.html', next=next_url)

@app.route('/signup', methods=['POST'])
def signup():
    # ... handles signup form submission ...
    return jsonify({'success': True, 'redirect': data.get('next') or '/detect'})

@app.route('/login', methods=['POST'])
def login():
    # ... handles login form submission ...
    return jsonify({'success': True, 'redirect': data.get('next') or '/detect'})
```

## Data Models

**No data model changes required.** The feature is purely UI-focused and leverages existing authentication infrastructure.

### Existing User Model (for context)

The `current_user()` helper returns a user dictionary with the following structure:

```python
{
    'id': str,        # UUID
    'email': str,     # User email
    'full_name': str  # User's display name
}
```

This dictionary is available in templates as `current_user` via the context processor.

## Correctness Properties

**Assessment:** This feature involves UI rendering, conditional display logic, and navigation. Property-based testing is **NOT appropriate** for the following reasons:

1. **UI Rendering:** The feature primarily involves HTML template rendering and CSS styling, which are not amenable to property-based testing
2. **Simple Conditional Logic:** The authentication state check (`{% if not current_user %}`) is a simple boolean condition, not a complex function with varied inputs
3. **Navigation Behavior:** Button clicks trigger browser navigation, which is better tested through integration/E2E tests
4. **Static Content:** The buttons have fixed labels, icons, and styling - no input variation to generate

**Alternative Testing Strategy:**

- **Snapshot Tests:** Verify rendered HTML output for authenticated vs. unauthenticated states
- **Integration Tests:** Verify button navigation and authentication flow end-to-end
- **Visual Regression Tests:** Ensure buttons render correctly across viewports
- **Accessibility Tests:** Verify ARIA labels, keyboard navigation, and color contrast

**Omitting Correctness Properties Section** as property-based testing does not apply to this UI-focused feature.

## Error Handling

### Authentication State Edge Cases

1. **Session Timeout During Page Load:**
   - **Scenario:** User's session expires between page load and button click
   - **Handling:** The `/auth` route already handles this - if `current_user()` is None, user sees login form

2. **Concurrent Sessions:**
   - **Scenario:** User logs in on another device while viewing home page
   - **Handling:** Home page buttons remain visible until page refresh; no error state needed

3. **Browser Back Navigation:**
   - **Scenario:** User logs in, clicks back to home page
   - **Handling:** Browser may show cached version with auth buttons; user can refresh to see updated state

### Responsive Layout Edge Cases

1. **Very Small Viewports (<320px):**
   - **Handling:** Existing CSS sets `width: 100%` for buttons, ensuring they don't overflow

2. **Four Buttons in Hero Section:**
   - **Handling:** Existing `flex-wrap: wrap` allows buttons to wrap to multiple rows on smaller screens

### Accessibility Edge Cases

1. **Screen Reader Announcement:**
   - **Handling:** `aria-label` attributes provide clear button descriptions
   - Example: "Sign up for a new account" vs. just "Sign Up"

2. **Keyboard Navigation:**
   - **Handling:** Standard `<a>` elements are keyboard navigable by default
   - Browser provides focus outline (Bootstrap overrides can be tested)

3. **Color Contrast:**
   - **Handling:** Existing button styles meet WCAG AA standards:
     - Primary green button: white text on green background (contrast ratio > 4.5:1)
     - Outline green button: green text on white background (contrast ratio > 4.5:1)

## Testing Strategy

### Unit Tests (Template Rendering)

**Test Framework:** pytest with Flask test client

**Test Cases:**

1. **Unauthenticated User - Buttons Visible:**
   ```python
   def test_hero_shows_auth_buttons_when_not_logged_in(client):
       """Verify Sign Up and Sign In buttons appear for guest users."""
       response = client.get('/')
       html = response.data.decode('utf-8')
       
       assert 'Sign Up' in html
       assert 'Sign In' in html
       assert 'bi-person-plus' in html  # Sign Up icon
       assert 'bi-box-arrow-in-right' in html  # Sign In icon
       assert response.status_code == 200
   ```

2. **Authenticated User - Buttons Hidden:**
   ```python
   def test_hero_hides_auth_buttons_when_logged_in(client, logged_in_session):
       """Verify Sign Up and Sign In buttons are hidden for authenticated users."""
       response = client.get('/')
       html = response.data.decode('utf-8')
       
       # Auth buttons should NOT appear
       assert 'Sign Up</a>' not in html or 'btn-primary-green' not in html
       
       # Core action buttons should still appear
       assert 'Start Detection' in html
       assert 'Supported Crops' in html
       assert response.status_code == 200
   ```

3. **Button Attributes - Accessibility:**
   ```python
   def test_auth_buttons_have_aria_labels(client):
       """Verify buttons have descriptive ARIA labels for screen readers."""
       response = client.get('/')
       html = response.data.decode('utf-8')
       
       assert 'aria-label="Sign up for a new account"' in html
       assert 'aria-label="Sign in to your account"' in html
   ```

4. **Button Links - Correct Targets:**
   ```python
   def test_auth_buttons_link_to_auth_route(client):
       """Verify both buttons navigate to /auth."""
       response = client.get('/')
       html = response.data.decode('utf-8')
       
       # Parse HTML and find auth button links
       from bs4 import BeautifulSoup
       soup = BeautifulSoup(html, 'html.parser')
       auth_buttons = soup.find_all('a', class_='btn', href='/auth')
       
       # Should have at least 2 auth buttons (Sign Up, Sign In)
       assert len(auth_buttons) >= 2
   ```

### Integration Tests (Authentication Flow)

**Test Framework:** Selenium or Playwright for E2E testing

**Test Cases:**

1. **Sign Up Flow from Home Page:**
   ```python
   def test_signup_flow_from_home_page(browser):
       """Verify complete signup flow from hero section button."""
       browser.get('http://localhost:5000/')
       
       # Click Sign Up button
       signup_btn = browser.find_element_by_text('Sign Up')
       signup_btn.click()
       
       # Should navigate to /auth
       assert '/auth' in browser.current_url
       
       # Fill signup form and submit
       browser.fill_form({
           'full_name': 'Test User',
           'email': 'test@example.com',
           'password': 'password123'
       })
       browser.submit_form()
       
       # Should redirect to /detect
       assert '/detect' in browser.current_url
       
       # Navigate back to home page
       browser.get('http://localhost:5000/')
       
       # Auth buttons should be hidden
       assert not browser.is_visible('Sign Up')
       assert not browser.is_visible('Sign In')
   ```

2. **Sign In Flow from Home Page:**
   ```python
   def test_signin_flow_from_home_page(browser, existing_user):
       """Verify complete signin flow from hero section button."""
       browser.get('http://localhost:5000/')
       
       # Click Sign In button
       signin_btn = browser.find_element_by_text('Sign In')
       signin_btn.click()
       
       # Should navigate to /auth
       assert '/auth' in browser.current_url
       
       # Fill signin form and submit
       browser.fill_form({
           'email': existing_user.email,
           'password': existing_user.password
       })
       browser.submit_form()
       
       # Should redirect to /detect
       assert '/detect' in browser.current_url
   ```

### Visual Regression Tests

**Test Framework:** Percy, Chromatic, or manual inspection

**Test Cases:**

1. **Desktop Layout (1920x1080):**
   - Unauthenticated: Verify 4 buttons in hero section (Sign Up, Sign In, Start Detection, Supported Crops)
   - Authenticated: Verify 2 buttons in hero section (Start Detection, Supported Crops)

2. **Tablet Layout (768x1024):**
   - Verify buttons wrap gracefully
   - Verify spacing and alignment

3. **Mobile Layout (375x667):**
   - Verify buttons stack vertically
   - Verify full-width button sizing
   - Verify touch-friendly sizing (44x44px minimum)

### Accessibility Tests

**Test Framework:** axe-core, WAVE, or manual testing with screen readers

**Test Cases:**

1. **Keyboard Navigation:**
   - Tab through hero section buttons
   - Verify focus order: Sign Up → Sign In → Start Detection → Supported Crops
   - Verify visible focus indicator on each button

2. **Screen Reader Compatibility:**
   - Test with NVDA, JAWS, or VoiceOver
   - Verify button labels are announced correctly
   - Verify icon-only buttons have text equivalents

3. **Color Contrast:**
   - Verify Sign Up button (white on green) meets WCAG AA
   - Verify Sign In button (green on white) meets WCAG AA
   - Verify focus states have sufficient contrast

4. **Touch Target Size:**
   - Verify buttons meet minimum 44x44px touch target on mobile
   - Existing CSS: `padding: 14px 32px` provides 44px+ height

### Responsive Layout Tests

**Test Framework:** Selenium with viewport resizing

**Test Cases:**

1. **Viewport Width > 768px:**
   - Verify buttons display in a horizontal row
   - Verify 16px gap between buttons
   - Verify no wrapping

2. **Viewport Width 576px - 768px:**
   - Verify buttons wrap to multiple rows if needed
   - Verify centered alignment

3. **Viewport Width < 576px:**
   - Verify buttons stack vertically
   - Verify full-width sizing
   - Verify centered alignment

## Summary

This design adds prominent Sign Up and Sign In buttons to the home page hero section with minimal code changes and no backend modifications. The implementation leverages existing CSS classes, authentication infrastructure, and routing logic. The feature enhances user onboarding while maintaining design consistency and accessibility standards.

**Key Implementation Points:**
- Single template file modification (index.html)
- No new CSS required (reuses existing button classes)
- No backend changes (leverages existing /auth route and context processor)
- Conditional rendering based on authentication state
- Responsive layout handled by existing flex-based CSS
- Accessibility ensured through ARIA labels and semantic HTML

**Testing Approach:**
- Unit tests for template rendering and conditional logic
- Integration tests for authentication flow end-to-end
- Visual regression tests for responsive layout
- Accessibility tests for keyboard navigation and screen readers
- No property-based testing (UI rendering not suitable for PBT)
