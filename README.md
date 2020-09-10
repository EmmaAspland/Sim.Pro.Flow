# Sim.Pro.Flow Logo
Sim.Pro.Flow is a decision support tool that automates the build of a discrete event simulation and allows for mapping, modelling and improving of system pathways.
___
## Features
*	Pre-process data into the correct format required
*	Extract the individual pathways from the data
*	Produce a summary word document of the raw data
*	Draw and visualise the system
*	Automate the building of the simulation model by extracting arrivals, services, networks and capacity levels
*	Calculate capacity levels based on percentage targets for wait days
*	Allow the user to edit input variables 
*	Run trials of the simulation
*	Collect the results and display in the form of tables and plots
*	Save all data and plots produced automatically
*	Export the simulation inputs used to allow for further analysis
___
## Usage
*	_pip install required versions of libraries – see requirements_versions.txt_
*	_navigate terminal to folder containing App.py_
*	_run App.py using python App.py_
___
Each of the main functions (mapping, modelling and improving) are explored through the following ways.

__Mapping__

Initially each individual within the input data is assigned a pathway, which is formed of a string of character codes corresponding to the order of the activities performed recorded by the date stamps. 
There are four different data levels that can be explored:

*	Raw pathways – 
This will investigate the exact pathways as they appear in the data. This allows for direct simulation of these exact pathways.
*	Full Transitions – 
The raw pathways are analysed to produce a transition matrix – the probability matrix that one activity follows another. This will allow for variation to be introduced within the confides of the probabilities observed within the data.
*	Clustered Transitions – 
This produces multiple smaller transition matrices, where pathways are grouped together based on their similarities. K-medoids clustering is used with a variety of distance metrics and the silhouette score to evaluate goodness of fit.
Furthermore, a new distance metric was developed namely modified Needleman-Wunsch algorithm that allows the user to define information about the activities. 
*	Process Centroids – 
This will use only the pathways that were chosen as the centroids of each cluster – The pathway that best represents that cluster.
The same clustering technique as above is used here but with the number of connections displayed and the differences from the non-clustered transitions is considered for goodness of fit.

__Modelling__

A discrete event simulation, using the python library [Ciw](https://ciw.readthedocs.io/en/latest/), can be automatically built from each of the data levels discussed above. The simulation can either be run in basic form (runs once) to collect in depth results and graphics, or through trials (multiple runs) allowing confidence intervals.

__Improving__

The simulation inputs including, arrivals, service rates, warm up times and capacity levels can all be customised by the user. 
The initial extraction of capacity levels is performed by taking the average number of each activity performed each named day i.e. based on the current performance of the system. Further analysis is available for calculating the amount of capacity required, through using a technique developed by Arruda et al (2020), ([Resource optimization for cancer pathways with aggregate diagnostic demand: a perishable inventory approach](https://academic.oup.com/imaman/advance-article/doi/10.1093/imaman/dpaa014/5864939?guestAccessKey=bf53ba01-ace0-4dff-ae56-c172fa169148)). This method uses a steady state technique which suggests the capacity required to achieve the percentage target of desired number of waiting days, selected by the user.
___
This tool was built as part of a learning exercise to contribute to a PhD project in collaboration with Velindre Cancer Centre. The main research goal was to build a decision support tool to allow for mapping, modelling and improving the clinical pathway for lung cancer patients. 

Sim.Pro.Flow is in prototype development phase and as such has not gone through extensive user testing or error checking. By using Sim.Pro.Flow the user takes on all responsibility to ensure that the process and as such all results are correct.

This work has resulted from research funded by a Cancer Research UK grant ‘Analysis and Modelling of a Single Cancer Pathway Diagnostics’ (Early Diagnosis Project Award A27882) and from a KESS2 grant under the project title ‘Smart Simulation and Modelling of Complex Cancer Systems’. Knowledge Economy Skills Scholarships (KESS) is a pan-Wales higher level skills initiative led by Bangor University on behalf of the HE sector in Wales. It is part funded by the Welsh Government’s European Social Fund (ESF) convergence programme for West Wales and the Valleys.
 ## Funder Logos
