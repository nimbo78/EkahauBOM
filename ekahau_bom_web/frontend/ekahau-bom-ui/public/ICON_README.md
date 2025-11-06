# Icons & Favicons

## Files Created

### ✅ SVG Icons (Created)
- `logo.svg` - Main logo for header (48x48)
- `favicon.svg` - Simplified favicon (32x32)

### 📋 PNG Icons (To Create)

To create PNG favicons from SVG:

#### Option 1: Online Tools
1. Open `favicon.svg` in https://cloudconvert.com/svg-to-ico
2. Convert to ICO (16x16, 32x32, 48x48 multi-size)
3. Save as `favicon.ico`

4. For Apple Touch Icon:
   - Open `logo.svg` in https://cloudconvert.com/svg-to-png
   - Resize to 180x180
   - Save as `apple-touch-icon.png`

#### Option 2: ImageMagick (Command Line)
```bash
# Create favicon.ico (multi-size)
magick convert favicon.svg -define icon:auto-resize=16,32,48 favicon.ico

# Create Apple Touch Icon
magick convert logo.svg -resize 180x180 apple-touch-icon.png

# Create OG/Twitter images
magick convert logo.svg -resize 1200x630 -background white -gravity center og-image.png
magick convert logo.svg -resize 1200x600 -background white -gravity center twitter-image.png
```

#### Option 3: Node.js (sharp library)
```bash
npm install sharp
node create-icons.js
```

```javascript
// create-icons.js
const sharp = require('sharp');

// Apple Touch Icon
sharp('logo.svg')
  .resize(180, 180)
  .png()
  .toFile('apple-touch-icon.png');

// OG Image
sharp('logo.svg')
  .resize(1200, 630)
  .png()
  .toFile('og-image.png');
```

## Logo Design

The logo combines:
- **Wi-Fi Signal Waves** (3 arcs) - representing wireless connectivity
- **Document/Checklist** - representing Bill of Materials
- **Checkmarks** - indicating completed tasks

### Color Scheme
- Primary: `#667EEA` (Indigo)
- Secondary: `#764BA2` (Purple)
- Accent: `#A78BFA` (Light Purple)
- Success: `#10B981` (Green for checkmarks)

### Usage
- Header: `<img src="logo.svg" alt="Ekahau BOM" width="40" height="40">`
- Favicon: Automatically loaded by browser from `<link>` tags

## SEO Meta Tags

All SEO meta tags have been added to `index.html`:
- Title: "Ekahau BOM Registry - Process and Visualize Wi-Fi Projects"
- Description: Comprehensive description for search engines
- Keywords: Ekahau, BOM, Wi-Fi, Wireless, Network Planning
- Open Graph tags for Facebook/LinkedIn sharing
- Twitter Card tags for Twitter sharing
- Theme color: `#667EEA`

## Browser Support

- **Modern Browsers**: Use `favicon.svg` (Chrome, Firefox, Edge, Safari 13+)
- **Older Browsers**: Use `favicon.ico` (IE11, Safari 12-)
- **iOS/iPadOS**: Use `apple-touch-icon.png`
- **PWA**: Can add `manifest.json` with icon references

## Future Improvements

1. Create PNG versions as described above
2. Add PWA manifest.json with icon references
3. Create og-image.png and twitter-image.png for social sharing
4. Add maskable icon for PWA (196x196 with safe zone)
