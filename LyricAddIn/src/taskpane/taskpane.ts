// taskpane/taskpane.ts

/**
 * Interface for the full response object from the Azure Function.
 * It uses the specific keys provided by your API.
 */
interface FunctionResponse {
  title: string;
  slide_count: number;
  slides: string[]; 
}

// Set up the button click event when the Office Add-in is ready
// taskpane/taskpane.ts

function attachButtonHandler() {
    // 1. Get the button element
    const createButton = document.getElementById("createSlidesButton");
    
    if (createButton) {
        // Use addEventListener for best practice
        createButton.addEventListener("click", createPresentation); 
        console.log("Button handler attached successfully.");
    } else {
        // This should appear in the console if attachment fails
        console.error("FAILURE: Button element #createSlidesButton not found!");
    }
}

Office.onReady((info) => {
    if (info.host === Office.HostType.PowerPoint) {
      /*
        // Check if the DOM is already ready, or wait for it.
        if (document.readyState === "complete" || document.readyState === "interactive") {
            attachButtonHandler();
        } else {
            // Fallback for browsers where DOMContentLoaded fires later
            document.addEventListener("DOMContentLoaded", attachButtonHandler);
        }*/
        attachButtonHandler();
    }
});

// ... rest of your code (createPresentation, createSlides, etc.) ...

const azureFunctionUrl: string = process.env.AZURE_FUNCTION_URL;

/**
 * Handles getting the URL, calling the Azure Function, and initiating slide creation.
 */
async function createPresentation(): Promise<void> {
  const urlInput = document.getElementById("urlInput") as HTMLInputElement;
  const urlToIngest = urlInput ? urlInput.value : '';
  
  // 🚨 IMPORTANT: REPLACE with your actual Azure Function URL
  const azureFunctionUrl: string = process.env.AZURE_FUNCTION_URL;

  if (!azureFunctionUrl) {
    console.error("Configuration error: Azure function URL is missing.");
    return;
  }

  if (!urlToIngest) {
    console.error("Please enter a URL.");
    // Optionally, alert the user or show a message in the task pane
    return;
  }

  try {
    // 1. Call the Azure Function (POST method)
    const response = await fetch(azureFunctionUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
        // Add any required authentication headers (e.g., API key) here
      },
      body: JSON.stringify({ url: urlToIngest })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    // 2. Parse the JSON response and cast it to the defined interface
    const data: FunctionResponse = await response.json(); 
    
    // 3. Initiate the slide creation logic
    await createSlides(data.title, data.slides);

  } catch (error) {
    console.error("Error creating slides:", error);
    // Handle API or network errors here
  }
}

/**
 * Uses Office.js API to create slides based on the API response.
 */
// taskpane/taskpane.ts (Corrected slide creation logic)

async function createSlides(presentationTitle: string, slideBodies: string[]): Promise<void> {
  try {
    await PowerPoint.run(async (context) => {
      const presentation = context.presentation;

      // Loop through each body content provided in the 'slides' array
      for (let i = 0; i < slideBodies.length; i++) {
        const bodyContent = slideBodies[i];
        
        let slideTitle: string;
        // The ID for the Title and Content layout (common layout)
        const slideLayoutId = 12; 

        if (i === 0) {
          slideTitle = presentationTitle;
        } else {
          slideTitle = `${presentationTitle} (Part ${i + 1})`; 
        }

        // FIX APPLIED HERE: Used 'slideLayoutId' instead of 'slideLayout'
        const newSlide = presentation.slides.add({ slideLayoutId: slideLayoutId });

        // Load shapes (placeholders) to manipulate them
        newSlide.load('shapes');
        await context.sync();
        const shapes = newSlide.shapes.items;

        // Find and set content for placeholders
        for (const shape of shapes) {
          if (shape.placeholderFormat) {
            shape.placeholderFormat.load('type');
            await context.sync();

            // Set the Title placeholder
            if (shape.placeholderFormat.type === PowerPoint.PlaceholderType.title) {
              shape.textFrame.insertText(slideTitle, PowerPoint.InsertLocation.replace);
            } 
            // Set the Body/Content placeholder
            else if (shape.placeholderFormat.type === PowerPoint.PlaceholderType.body) {
              const text = bodyContent.replace(/\\n/g, '\n'); 
              shape.textFrame.insertText(text, PowerPoint.InsertLocation.replace);
            }
          }
        }
      }

      await context.sync();
      console.log("Slides created successfully.");
    });
  } catch (error) {
    console.error("Office.js run error:", error);
    throw error;
  }
}