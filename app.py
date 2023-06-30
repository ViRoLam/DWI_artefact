import matplotlib.pyplot as plt
import numpy as np
from tkinter import *
from tkinter import filedialog, messagebox
import nibabel as nib
import os
import sys
from tkinter import ttk
import numpy as np
import xlsxwriter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import cv2
import copy
import tkinter.font as font




CHOSEN_FOLDER = ""
ALL_FILES = ""
IMAGE_FILES = ""
NUMBER_OF_DIRECTIONS = 0
IMAGE_HEIGHT = 0
IMAGE_WIDTH = 0
IMAGE_DEPTH = 0
VERBOSE_BUFFER = "\n\r" + "-" * 50 + "\n\r"
THRESHOLD = 0.4
ALL_ARTIFACTS = [] #a list containing all artifacts that have been found
DONE = False #To know if it is okay to store the excel file
MANUALLY_CHECKED = False
IS_ARTIFACT = False


EXCEL_FILE = f"QC_Python_script.xlsx"
WORKBOOK = None 
WORKSHEET = None 

def init_spreadsheet(file):
    global WORKBOOK,WORKSHEET,EXCEL_FILE
    print(f"[*]Creating EXCEL File {file}")
    WORKBOOK = xlsxwriter.Workbook(file)
    WORKSHEET = WORKBOOK.add_worksheet()
    WORKSHEET.set_column('A:A', 4)
    WORKSHEET.set_column('B:B', 37)
    WORKSHEET.set_column('C:C', 23)
    WORKSHEET.set_column('D:D', 12)
    WORKSHEET.write('A1', 'Index')
    WORKSHEET.write('B1', 'ID')
    WORKSHEET.write("C1","QC (1=no artifact, 0=artifact)")
    WORKSHEET.write("D1","Volume indices")
    return WORKBOOK, WORKSHEET

def save_excel():
    global IMAGE_FILES,ALL_ARTIFACTS
    if DONE:
        f = filedialog.asksaveasfilename(defaultextension=".xlsx")
        WORKBOOK,WORKSHEET = init_spreadsheet(f)
        for indx,patient_file in enumerate(IMAGE_FILES):
            WORKSHEET.write(f"A{indx+2}",str(indx+1))
            WORKSHEET.write(f"B{indx+2}",str(patient_file))
        #f.write()
        for indx,contains_artifact in ALL_ARTIFACTS:
            if len(contains_artifact)>0:
                WORKSHEET.write(f"C{indx+2}","0")
                WORKSHEET.write(f"D{indx+2}",",".join(contains_artifact))
            else:
                WORKSHEET.write(f"C{indx+2}","1")
        WORKBOOK.close()


def CONFIRM_ARTIFACT():
    global IS_ARTIFACT, MANUALLY_CHECKED
    IS_ARTIFACT = True 
    MANUALLY_CHECKED = True 

def REFUTE_ARTIFACT():
    global IS_ARTIFACT, MANUALLY_CHECKED
    IS_ARTIFACT = False 
    MANUALLY_CHECKED = True


def find_artifacts(verbose=True):
    global MANUALLY_CHECKED ,IS_ARTIFACT, WAIT_FOR_CONFIRMATION, CHECKBOX_CHECK_MANUAL,EXCEL_FILE_BUTTON,LOAD_FOLDER_B,chart_type,figure,axs,DONE,TOTAL_NUMBER_OF_ARTIFACTS_FOUND_LABEL,specific_pb,NUMBER_OF_ARTIFACTS_FOUND_LABEL,PROCESSING_IMAGE_LABEL,general_pb,window,THRESHOLD,CHOSEN_FOLDER, FOLDER_LABEL, NUMBER_OF_PATIENTS_LABEL, ALL_FILES, IMAGE_FILES, NUMBER_OF_DIRECTIONS, HEIGHT_LABEL, WIDTH_LABEL, DEPTH_LABEL,IMAGE_HEIGHT,IMAGE_WIDTH,IMAGE_DEPTH
    threshold_slider["state"]  = "disabled" #So that you cannot change the value of the slider during the processing
    #general_pb["maximum"]=len(IMAGE_FILES)
    DONE = False
    general_pb["value"]=0
    LOAD_FOLDER_B["state"] = "disabled"
    all_artifacts = []
    MANUALLY_CHECKED = False
    for i, image in enumerate(IMAGE_FILES):
        specific_pb["value"]=0
        general_pb["value"]=i/len(IMAGE_FILES)*100
        PROCESSING_IMAGE_LABEL.config(text=f"Processing:{image}")
        window.update()
        if verbose:
            print(f"[*]Processing file [{i}]: {image}")
        doc = nib.load(os.path.join(CHOSEN_FOLDER, image))

        img = doc.get_fdata()
        if img.shape[0] != IMAGE_HEIGHT or img.shape[1] != IMAGE_WIDTH or img.shape[2] != IMAGE_DEPTH or img.shape[3] != NUMBER_OF_DIRECTIONS:
            messagebox.showerror(
                "Open Source File",
                f"Warning !\nFile {image} is not in the same format as the other files !")


        '''
        Processing artifacts
        '''
        contains_line_artifact = []
        contains_grid_artifact = []
        img_shape = img.shape
        #print(img_shape)
        NUMBER_OF_ARTIFACTS_FOUND_LABEL.config(text=f"Artifacts found:{len(contains_line_artifact+contains_grid_artifact)}")

        for direction in range(img.shape[3]):
            '''
            Processing line artifacts
            '''
            #direction = 18

            slices_averages = [np.mean(img[:, :, depth, direction])
                               for depth in range(img_shape[2])]

            v = []
            for x in range(1, img_shape[2] - 1):
                v.append((abs(slices_averages[x - 1] - slices_averages[x]) + abs(
                    slices_averages[x + 1] - slices_averages[x])) / np.mean(slices_averages))

            if any(np.array(v)>THRESHOLD):
                
                axs[0].cla()
                axs[1].cla()
                axs[0].set_ylim([0, 2])
                axs[0].plot(v)
                axs[0].plot([THRESHOLD]*len(slices_averages),"r--",label="threshold",linewidth=1)
                axs[0].set_title("Change")
                
                axs[1].imshow(img[int(img_shape[0]/2)+2,:,:,direction],cmap='gray')
                axs[1].set_title('image')
                chart_type.draw()
                if CHECK_MANUALLY.get()==1:
                    while True:
                        window.update()
                        if MANUALLY_CHECKED:
                            if IS_ARTIFACT:
                                contains_line_artifact.append(str(direction+1))
                            MANUALLY_CHECKED = False
                            break
                else:
                    contains_line_artifact.append(str(direction+1))
                NUMBER_OF_ARTIFACTS_FOUND_LABEL.config(text=f"Artifacts found:{len(contains_line_artifact+contains_grid_artifact)}")
                TOTAL_NUMBER_OF_ARTIFACTS_FOUND_LABEL.config(text=f"Total number of Artifacts found:{sum([len(i[1]) for i in ALL_ARTIFACTS])+len(contains_line_artifact+contains_grid_artifact)}")
                print(f"[!]Found line artifact in image: {IMAGE_FILES[i]}, direction: {direction+1}")
            
            '''Processing grid artifacts'''
            
            #if not direction-1 in [1,2]+[2+11*d for d in range(int((NUMBER_OF_DIRECTIONS-2)/11))]:
                #print(direction)
            for depth in range(img.shape[2]):
                print(f"Processing direction: {direction}, depth: {depth}")
                grid_img = img[:,:,depth,direction]
                dft = cv2.dft(np.float32(grid_img), flags=cv2.DFT_COMPLEX_OUTPUT)

                #Rearranges a Fourier transform X by shifting the zero-frequency 
                #component to the center of the array.
                #Otherwise it starts at the tope left corenr of the image (array)
                dft_shift = np.fft.fftshift(dft)

                ##Magnitude of the function is 20.log(abs(f))
                #For values that are 0 we may end up with indeterminate values for log. 
                #So we can add 1 to the array to avoid seeing a warning. 
                magnitude_spectrum =  20 * np.log(cv2.magnitude(dft_shift[:, :, 0], dft_shift[:, :, 1]))


                # Circular HPF mask, center circle is 0, remaining all ones
                #Can be used for edge detection because low frequencies at center are blocked
                #and only high frequencies are allowed. Edges are high frequency components.
                #Amplifies noise.

                rows, cols = grid_img.shape
                crow, ccol = int(rows / 2), int(cols / 2)

                mask = np.ones((rows, cols), np.uint8)
                r = 24 
                center = [crow, ccol]
                x, y = np.ogrid[:rows, :cols]
                mask_area = (x - center[0]) ** 2 + (y - center[1]) ** 2 <= r*r
                mask[mask_area] = 0

                mask_area1 = abs(0*x+y-center[0]) <= 5
                magnitude_spectrum = np.uint8(magnitude_spectrum)
                visual_mag = copy.copy(magnitude_spectrum)
                #magnitude_spectrum[mask_area] =0
                #magnitude_spectrum[mask_area1] =0

                gray = cv2.GaussianBlur(grid_img, (5,5), 1)
                scale = 1
                delta = 5
                ddepth = cv2.CV_16S
                grad_x = cv2.Sobel(gray, ddepth, 1, 0, ksize=3, scale=scale, delta=delta, borderType=cv2.BORDER_DEFAULT)
                # Gradient-Y
                # grad_y = cv.Scharr(gray,ddepth,0,1)
                grad_y = cv2.Sobel(gray, ddepth, 0, 1, ksize=3, scale=scale, delta=delta, borderType=cv2.BORDER_DEFAULT)
                
                
                abs_grad_x = cv2.convertScaleAbs(grad_x)
                abs_grad_y = cv2.convertScaleAbs(grad_y)
                
                
                grad = cv2.addWeighted(abs_grad_x, 0.5, abs_grad_y, 0.5, 0)
                #ret, thresh = cv2.threshold(gray, 20, 255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY)
                #if np.mean(thresh)>45:
                #print(f"[!]Found grid artifact in image: {IMAGE_FILES[i]}, direction: {direction+1}, depth:{depth},strenght:{np.mean(thresh)}")
                axs[0].cla()
                axs[1].cla()
                axs[0].imshow(grad)
                #axs[0].plot([THRESHOLD]*len(slices_averages),"r--",label="threshold",linewidth=1)
                axs[0].set_title("FFT of image")
                axs[1].imshow(grid_img,cmap='gray')
                axs[1].set_title('image')
                chart_type.draw()
                window.update()
                if CHECK_MANUALLY.get()==1:

                    while True:
                        window.update()
                        if MANUALLY_CHECKED:
                            if IS_ARTIFACT:
                                contains_grid_artifact.append(str(direction+1))
                            MANUALLY_CHECKED = False
                            break
                else:
                    contains_grid_artifact.append(str(direction+1))
                    IS_ARTIFACT = True

                NUMBER_OF_ARTIFACTS_FOUND_LABEL.config(text=f"Artifacts found:{len(contains_line_artifact+contains_grid_artifact)}")
                TOTAL_NUMBER_OF_ARTIFACTS_FOUND_LABEL.config(text=f"Total number of Artifacts found:{sum([len(i[1]) for i in ALL_ARTIFACTS])+len(contains_line_artifact+contains_grid_artifact)}")
                #if IS_ARTIFACT:
                #    break #Once an artifact has been found we don't need to continue to check for artifacts for that direction
            #l = [observe_grid_pattern(img[:,:,depth,direction],direction) for depth in range(img.shape[2])]

                
            specific_pb["value"] = direction/NUMBER_OF_DIRECTIONS*100
            window.update()
        ALL_ARTIFACTS.append([i,contains_line_artifact+contains_grid_artifact])
        
    threshold_slider["state"]  = "normal"
    LOAD_FOLDER_B["state"] = "normal"
    specific_pb["value"] = 0
    general_pb["value"]=0
    NUMBER_OF_ARTIFACTS_FOUND_LABEL.config(text=f"Artifacts found:")
    PROCESSING_IMAGE_LABEL.config(text=f"Processing:")
    if len(IMAGE_FILES)>0:
        DONE = True
        EXCEL_FILE_BUTTON["state"] = "normal"

def load_files(CHOSEN_FOLDER, verbose=True, sort=True):
    # All the files that are in the directory
    ALL_FILES = os.listdir(CHOSEN_FOLDER)

    # The images we will be working with, we chose the pdf format
    IMAGE_FILES = list(filter(lambda x: x.endswith("nii.gz"), ALL_FILES))[:20]
    if sort:
        IMAGE_FILES = sorted(IMAGE_FILES)
    if verbose:
        print("[*]Images retrieved:")
        for img in IMAGE_FILES:
            print("[+]", img)
        print(VERBOSE_BUFFER)
    return ALL_FILES, IMAGE_FILES, NUMBER_OF_DIRECTIONS


def load_data_info(IMAGE_FILES):
    image = IMAGE_FILES[0]
    doc = nib.load(os.path.join(CHOSEN_FOLDER, image))
    arr = doc.get_fdata()
    return arr.shape


def loadtemplate():
    global CHOSEN_FOLDER, FOLDER_LABEL, NUMBER_OF_PATIENTS_LABEL, ALL_FILES, IMAGE_FILES, NUMBER_OF_DIRECTIONS, HEIGHT_LABEL, WIDTH_LABEL, DEPTH_LABEL,IMAGE_HEIGHT,IMAGE_WIDTH,IMAGE_DEPTH
    filename = filedialog.askdirectory()
    if filename:
        try:
            CHOSEN_FOLDER = filename
            FOLDER_LABEL.config(
                text=f"Loaded folder:{os.path.basename(CHOSEN_FOLDER)}")
            ALL_FILES, IMAGE_FILES, NUMBER_OF_DIRECTIONS = load_files(
                CHOSEN_FOLDER)

            if len(IMAGE_FILES) == 0:
                raise Exception("No niftii files found")
            NUMBER_OF_PATIENTS_LABEL.config(
                text=f"patients:{len(IMAGE_FILES)}")
            IMAGE_HEIGHT, IMAGE_WIDTH, IMAGE_DEPTH, NUMBER_OF_DIRECTIONS = load_data_info(
                IMAGE_FILES)

            NUMBER_OF_DIRECTIONS_LABEL.config(
                text=f"directions:{NUMBER_OF_DIRECTIONS}")

            HEIGHT_LABEL.config(text=f"height:{IMAGE_HEIGHT}")
            WIDTH_LABEL.config(text=f"width:{IMAGE_WIDTH}")
            DEPTH_LABEL.config(text=f"depth:{IMAGE_DEPTH}")

            # FOLDER_LABEL.update()
            # self.settings["template"].set(filename)
        except Exception as e:
            messagebox.showerror(
                "Open Source File", f"Failed to read directory \n{filename}\nerr:{str(e)}")


window = Tk()

window.title("Automatic Quality control")
window.geometry("1100x800+200+50")
window.resizable(False, False)


label_font = font.Font(family='Calibri', size=17)
big_font = font.Font(family='Calibri', size=40)
medium_font = font.Font(family='Calibri', size=25)


s = ttk.Style()
s.theme_use('clam')
s.configure("red.Horizontal.TProgressbar",troughcolor ='gray', background='blue')


LineCanvas =Canvas(window, width=window.winfo_screenwidth(), height=window.winfo_screenheight())
LineCanvas.place(x=0,y=0)
# Create a line in canvas widget
LineCanvas.create_line(400, 0, 400, window.winfo_screenheight(), width=2)
LineCanvas.create_line(0, 120, 400, 120, width=2)
LineCanvas.create_line(0, 250, 400, 250, width=2)
LineCanvas.create_line(0, 420, 400, 420, width=2)
LineCanvas.create_line(0, 550, 400, 550, width=2)
LineCanvas.create_line(400, 180, window.winfo_screenwidth(), 180, width=2)
LineCanvas.create_line(400, 660, window.winfo_screenwidth(), 660, width=2)





CHOOSE_FOLDER_LABEL = Label(window, text="Choose folder:")
CHOOSE_FOLDER_LABEL.place(x=10,y=30)
CHOOSE_FOLDER_LABEL["font"] = label_font

LOAD_FOLDER_B = Button(window, text="Load folder", command=loadtemplate, width=10,height=1)
LOAD_FOLDER_B.place(x=160,y=30)
LOAD_FOLDER_B["font"] = medium_font


FOLDER_LABEL = Label(window, text="Loaded folder:")
FOLDER_LABEL.place(x=10,y=80)
FOLDER_LABEL["font"] = label_font


#Put a line here 

INFO_LABEL = Label(window, text="Info:")
INFO_LABEL.place(x=10,y=130)
INFO_LABEL["font"] = label_font

NUMBER_OF_PATIENTS_LABEL = Label(window, text="patients:")
NUMBER_OF_PATIENTS_LABEL.place(x=40,y=170)
NUMBER_OF_PATIENTS_LABEL["font"] = label_font

NUMBER_OF_DIRECTIONS_LABEL = Label(window, text="directions:")
NUMBER_OF_DIRECTIONS_LABEL.place(x=40,y=210)
NUMBER_OF_DIRECTIONS_LABEL["font"] = label_font

#Put a line here 

VOLUME_INFO_LABEL = Label(window, text="Volume:")
VOLUME_INFO_LABEL.place(x=10,y=260)
VOLUME_INFO_LABEL["font"] = label_font

HEIGHT_LABEL = Label(window, text="height:")
HEIGHT_LABEL.place(x=40,y=300)
HEIGHT_LABEL["font"] = label_font

WIDTH_LABEL = Label(window, text="width:")
WIDTH_LABEL.place(x=40,y=340)
WIDTH_LABEL["font"] = label_font

DEPTH_LABEL = Label(window, text="depth:")
DEPTH_LABEL.place(x=40,y=380)
DEPTH_LABEL["font"] = label_font


INFO_LABEL1 = Label(window, text="Parameters:")
INFO_LABEL1.place(x=10,y=430)
INFO_LABEL1["font"] = label_font

THRESHOLD_LABEL = Label(window, text="threshold:")
THRESHOLD_LABEL.place(x=40,y=470)
THRESHOLD_LABEL["font"] = label_font


def threshold_slider_changed(event):
    global THRESHOLD  
    THRESHOLD = threshold_slider.get()

threshold_slider = Scale(
    window,
    from_=0.01,
    to=1,
    resolution=0.001,
    orient='horizontal',
    command=threshold_slider_changed,
    sliderrelief='flat', 
    highlightthickness=0, 
    fg='black',
    troughcolor='#73B5FA',
    activebackground='#1065BF'
)
threshold_slider.set (THRESHOLD)
threshold_slider.place(x=130,y=450,width=200)
threshold_slider["font"] = label_font


CHECK_MANUALLY = IntVar()

CHECKBOX_CHECK_MANUAL = Checkbutton(
    window, 
    text='Check  artifacts manually',
    onvalue=1,
    offvalue=0,
    variable=CHECK_MANUALLY,
    activeforeground="blue")

CHECKBOX_CHECK_MANUAL.place(x=40,y=510)
CHECKBOX_CHECK_MANUAL["font"] = label_font


FIND_ARTIFACTS = Button(window, text="Find Artifacts",
                        command=find_artifacts, width=12, height=3)
FIND_ARTIFACTS.place(x=50,y=570)
FIND_ARTIFACTS["font"] = big_font



GENERAL_PROGRESS_LABEL = Label(window, text="General progress:")
GENERAL_PROGRESS_LABEL.place(x=40,y=730)
GENERAL_PROGRESS_LABEL["font"] = label_font

general_pb = ttk.Progressbar(
    window,
    orient='horizontal',
    mode="determinate",
    length=320,
    style="red.Horizontal.TProgressbar"
)
general_pb.place(x=40,y=760)
general_pb["value"]=0





#Now for the right hand side of the window 

RESULTS_LABEL = Label(window, text="Results:")
RESULTS_LABEL.place(x=420,y=30)
RESULTS_LABEL["font"] = label_font


PROCESSING_IMAGE_LABEL = Label(window, text="Processing:")
PROCESSING_IMAGE_LABEL.place(x=450,y=70)
PROCESSING_IMAGE_LABEL["font"] = label_font


NUMBER_OF_ARTIFACTS_FOUND_LABEL = Label(window, text="Artifacts found:")
NUMBER_OF_ARTIFACTS_FOUND_LABEL.place(x=450,y=110)
NUMBER_OF_ARTIFACTS_FOUND_LABEL["font"] = label_font


specific_pb = ttk.Progressbar(
    window,
    orient='horizontal',
    mode="determinate",
    length=500,
    style="red.Horizontal.TProgressbar"
)
specific_pb.place(x=450,y=140)
specific_pb["value"]=0


#figure = plt.Figure(figsize=(6,5), dpi=100)
#ax = figure.add_subplot(111)
figure, axs = plt.subplots(1,2,figsize=(7,4))
chart_type = FigureCanvasTkAgg(figure, window)
chart_type.get_tk_widget().place(x=401,y=190)
#df = df[['First Column','Second Column']].groupby('First Column').sum()
#df.plot(kind='Chart Type such as bar', legend=True, ax=ax)
axs[0].set_title('change')
axs[1].set_title('img')

CONFIRM_ARTIFACT_BUTTON = Button(window, text="artifact",
                        command=CONFIRM_ARTIFACT, width=10, height=2)
CONFIRM_ARTIFACT_BUTTON.place(x=550,y=600)

REFUTE_ARTIFACT_BUTTON = Button(window, text="no artifact",
                        command=REFUTE_ARTIFACT, width=10, height=2)
REFUTE_ARTIFACT_BUTTON.place(x=900,y=600)


TOTAL_NUMBER_OF_ARTIFACTS_FOUND_LABEL = Label(window, text="Total number of Artifacts found:")
TOTAL_NUMBER_OF_ARTIFACTS_FOUND_LABEL.place(x=430,y=670)
TOTAL_NUMBER_OF_ARTIFACTS_FOUND_LABEL["font"] = label_font


EXCEL_FILE_LABEL = Label(window, text="Save results in excel file:")
EXCEL_FILE_LABEL.place(x=430,y=720)
EXCEL_FILE_LABEL["font"] = label_font



EXCEL_FILE_BUTTON = Button(window, text="Save",
                        command=save_excel, width=7, height=1)
EXCEL_FILE_BUTTON.place(x=670,y=710)
EXCEL_FILE_BUTTON["state"] = "disabled"
EXCEL_FILE_BUTTON["font"] =big_font


window.mainloop()
