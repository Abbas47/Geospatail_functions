# sentinel

• This section of data_acquisition is dedicated to downloading the sentinel satellite imagery using sentinelsat API.<br>
1. data_acquisition_sentinel.ipynb:<br>
This script can download the sentinel satellite imagery using the sentinelsat API. The product will be downloaded in .SAFE format which consists of separate bands in jp2 format.<br>
Note: A step-by-step guide to run the script is jotted down on the confluence page. To run the script, the user just needs to provide the relevant input in the "User Input" block.
confluence page link: https://littleplacelabs.atlassian.net/wiki/spaces/PE/pages/110395405/Step-by-Step+Guide+for+Acquiring+Sentinel+Imagery+using+script
2. convert_jp2_to_tiff.py:<br>
This script can be used to convert the jp2 image to tiff format.<br>
Note: A step-by-step guide to run the script is jotted down on the confluence page. To run the script, the user just needs to provide the relevant input in the "User Input" block.
confluence page link: https://littleplacelabs.atlassian.net/wiki/spaces/PE/pages/108953617/Step-by-Step+Guide+for+Conversion+of+Sentinel-2+MSI+Data+JP2+to+TIFF
3. requirments.txt:<br>
Install all required libraries using the requirement.txt.<br>
