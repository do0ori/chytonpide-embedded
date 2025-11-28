// TFT_eSPI setup.h file for ESP32-S3-DevKitC-1
// HiLetgo 240X320 Resolution 2.8" SPI TFT LCD Display Touch Panel ILI9341 

#define USER_SETUP_INFO "User_Setup"

#define ILI9341_DRIVER

// For ST7735, ST7789 and ILI9341 ONLY, define the colour order IF the blue and red are swapped on your display
// Try ONE option at a time to find the correct colour order for your display
//  #define TFT_RGB_ORDER TFT_RGB  // Colour order Red-Green-Blue
//  #define TFT_RGB_ORDER TFT_BGR  // Colour order Blue-Green-Red

// For ST7789, ST7735, ILI9163 and GC9A01 ONLY, define the pixel width and height in portrait orientation
#define TFT_WIDTH  240 // ST7789 240 x 240 and 240 x 320
#define TFT_HEIGHT 320 // ST7789 240 x 320

// If colours are inverted (white shows as black) then uncomment one of the next
// 2 lines try both options, one of the options should correct the inversion.

// #define TFT_INVERSION_ON
// #define TFT_INVERSION_OFF

#define TFT_CS   1 
#define TFT_MOSI 41 
#define TFT_SCLK 40
#define TFT_MISO MISO 

#define TFT_DC   42
#define TFT_RST  2

#define LOAD_GLCD
#define LOAD_FONT2
#define LOAD_FONT4
#define LOAD_FONT6
#define LOAD_FONT7
#define LOAD_FONT8
#define LOAD_GFXFF

#define SMOOTH_FONT

#define SPI_FREQUENCY   40000000

#define SPI_TOUCH_FREQUENCY  2500000

#define USE_HSPI_PORT