// write a function to
// find all images without alternate text
// and give them a red border
function highlightImagesWithoutAltText() {
    // get all images on the page
    const images = document.getElementsByTagName('img');
    for (let i = 0; i < images.length; i++) {
        const img = images[i];
        // check if the image has an alt attribute
        if (!img.hasAttribute('alt') || img.getAttribute('alt').trim() === '') {
            // if not, add a red border
            img.style.border = '2px solid red';
        }
    }
}
// run the function
highlightImagesWithoutAltText();