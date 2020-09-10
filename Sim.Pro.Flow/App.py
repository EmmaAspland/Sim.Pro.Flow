from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import wx.lib.scrolledpanel as scrolled
import time
import queue as Queue
from threading import Thread 
from pubsub import pub
import math
import copy

import pandas as pd
import numpy as np
import textdistance
import openpyxl

import wx
import wx.lib.mixins.inspection as WIT
import os
from os import path

import wx.grid as gridlib
import wx.adv
import Functions
import imp
algo = imp.load_source('algo', 'src/ModNW_Algo.py')

#============== Global ===============
class CanvasFrame(wx.Panel):
    """Single panel plotting frame."""
    def __init__(self, parent, DataPanel, canvasPanel, plotParent):
        """Constructs plotting canvas with toolbar - hold image as Sim.Pro.Flow Logo."""
        wx.Panel.__init__(self, parent)
        self.canvasPanel = canvasPanel
        self.DataPanel = DataPanel
        self.plotParent = plotParent

        self.mainsizer = wx.BoxSizer(wx.VERTICAL)
        self.hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.hsizer.AddSpacer(10)
        self.update_button = wx.Button(self, label='Update')
        self.update_button.Bind(event=wx.EVT_BUTTON, handler=self.onPlotSelect)
        self.hsizer.Add(self.update_button)
        self.hsizer.AddSpacer(10)
        self.plot_options = []
        self.plot_selection = wx.Choice(self, choices=self.plot_options, size=(200, 25))
        self.hsizer.Add(self.plot_selection)
        self.hsizer.AddSpacer(10)
        self.view_button = wx.Button(self, label='View')
        self.view_button.Bind(event=wx.EVT_BUTTON, handler=self.onView)
        self.hsizer.Add(self.view_button)
        self.mainsizer.Add(self.hsizer)

        self.figure = Figure()
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.mainsizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.EXPAND)
        self.SetSizer(self.mainsizer)
        self.Fit()

        if self.plotParent == "Cluster":
            hold_plot = self.canvasPanel.plot_names[0] 
        if self.plotParent == "Capacity":
            hold_plot = ''
        self.axes = self.figure.add_subplot(111)
        self.add_plot(hold_plot)
        self.figure.subplots_adjust(bottom=0, top=1, left=0, right=1)
        self.add_toolbar() 

    def add_toolbar(self):
        """Adds the navigation toolbar to the plotting canvas. """
        self.toolbar = NavigationToolbar(self.canvas)
        self.toolbar.Realize()
        self.mainsizer.Add(self.toolbar, 0, wx.LEFT | wx.EXPAND)
        self.toolbar.update()

    def add_plot(self, plot):    
        """Adds image to plot space."""
        if plot == '':
            img = plt.imread("Sim.Pro.Flow_Logo.png")
        else: 
            img = plt.imread(plot)
        self.axes.clear()
        self.axes.imshow(img)   
        self.axes.set_xticks([])
        self.axes.set_yticks([])
        self.axes.axis('equal')

    def onPlotSelect(self, event):
        """Updates the choice box of plot view options."""
        self.plot_selection.Clear()
        if self.plotParent == "Capacity":
            cap_plot_names = [name for name in self.canvasPanel.CalculatedCapacity.keys()]
            cap_plot_names = cap_plot_names[1:]
            self.plot_selection.AppendItems(cap_plot_names)
        if self.plotParent == "Cluster":
            self.plot_selection.AppendItems(self.canvasPanel.plot_names)
    
    def onView(self, event):
        """Selects plot to add to plot space."""
        plot = self.plot_selection.GetString(self.plot_selection.GetCurrentSelection())
        if self.plotParent == "Cluster":
            location = 'Plots/Process_Violin_Plots/'
        if self.plotParent == "Capacity":
            location = 'Plots/Capacity/'
        get_plot = self.DataPanel.SaveLoc + location + plot + '.png'
        self.add_plot(get_plot)


class ResultsGridPanel(wx.Panel):
    """Grid panel placeholder"""
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)  
        """Creates grid space that expands to panel."""
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddSpacer(20)
        
        self.ResultsGrid = gridlib.Grid(self)
        self.ResultsGrid.CreateGrid(0,0)
        sizer.Add(self.ResultsGrid, 1, wx.EXPAND | wx.ALL)

        self.SetSizer(sizer)


#============== Data Main Panel ===============
class DataPanel(wx.Panel):
    """Main data tab Panel."""
    def __init__(self, parent):
        """Set up the data panel layout.
        
        Split window:
        Left Top - data options
        Left Bottom - Empty grid to be filled
        Right - Blank placeholder      
        """
        wx.Panel.__init__(self, parent=parent) 
        self.data = pd.DataFrame()
        self.headers = []
        self.activity_codes = {}
        self.target = 30

        topSplitter = wx.SplitterWindow(self)
        LeftSplitter = wx.SplitterWindow(topSplitter)
        LeftSplitter.SetBackgroundColour(wx.Colour(250, 135, 72))   
        
        self.panel = wx.Panel(LeftSplitter)

        # selection box
        selection_box = wx.StaticBox(self.panel, -1, label='Selection')
        selection_sizer = wx.StaticBoxSizer(selection_box, wx.VERTICAL)
        selection_sizer.AddSpacer(10)
        selection_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        selection_hsizer.AddSpacer(5)

        self.browse_save_loc = wx.Button(self.panel, label='Select save location')
        self.browse_save_loc.Bind(event=wx.EVT_BUTTON, handler=self.onSaveLoc)
        selection_hsizer.Add(self.browse_save_loc)
        selection_hsizer.AddSpacer(130)
        self.browse_button = wx.Button(self.panel, label='Select data')
        self.browse_button.Bind(event=wx.EVT_BUTTON, handler=self.onSelectData)
        self.browse_button.Disable()
        selection_hsizer.Add(self.browse_button)
        selection_sizer.Add(selection_hsizer)

        # Format box
        format_box = wx.StaticBox(self.panel, -1, label='Format')
        format_sizer = wx.StaticBoxSizer(format_box, wx.VERTICAL)
        format_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        format_hsizer.AddSpacer(5)
        self.columns_button = wx.Button(self.panel, label = "Select columns")
        self.columns_button.Bind(event=wx.EVT_BUTTON, handler=self.getonHeaders(self.data))
        self.columns_button.Disable()
        format_hsizer.Add(self.columns_button)
        format_hsizer.AddSpacer(30)
        # Needs to be really long to not cut off text.
        self.running_text = wx.StaticText(self, label='                                            ')
        self.running_text.SetBackgroundColour(wx.Colour(250, 135, 72))
        format_hsizer.Add(self.running_text)  
        format_sizer.Add(format_hsizer)
        format_sizer.AddSpacer(10)
        format_hsizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        format_hsizer_1.AddSpacer(5)
        select_text = wx.StaticText(self.panel, label='OR Select the following columns:')
        format_hsizer_1.Add(select_text)
        format_sizer.Add(format_hsizer_1)
        format_sizer.AddSpacer(10)
        format_hsizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        format_hsizer_2.AddSpacer(10)
        id_text = wx.StaticText(self.panel, label='Unique Id')
        format_hsizer_2.Add(id_text)
        format_hsizer_2.AddSpacer(80)
        activity_text = wx.StaticText(self.panel, label='Activity')
        format_hsizer_2.Add(activity_text)
        format_hsizer_2.AddSpacer(85)
        dates_text = wx.StaticText(self.panel, label='Dates')
        format_hsizer_2.Add(dates_text)
        format_sizer.Add(format_hsizer_2)
        format_sizer.AddSpacer(10)
        format_hsizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        format_hsizer_3.AddSpacer(5)
        self.id_choice = wx.Choice(self.panel, choices=[])
        format_hsizer_3.Add(self.id_choice)
        format_hsizer_3.AddSpacer(20)
        self.activity_choice = wx.Choice(self.panel, choices=[])
        format_hsizer_3.Add(self.activity_choice)
        format_hsizer_3.AddSpacer(20)
        self.dates_choice = wx.Choice(self.panel, choices=[])
        format_hsizer_3.Add(self.dates_choice)
        format_sizer.Add(format_hsizer_3)
        format_sizer.AddSpacer(10)
        format_hsizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        format_hsizer_3.AddSpacer(5)
        # Needs to be really long to not cut off text.
        self.running_format_text = wx.StaticText(self.panel, label='                                            ')
        self.running_format_text.SetBackgroundColour(wx.Colour(250, 135, 72))
        format_hsizer_3.Add(self.running_format_text)
        format_hsizer_3.AddSpacer(150)
        self.format_button = wx.Button(self.panel, label='Format')
        self.format_button.Bind(event=wx.EVT_BUTTON, handler=self.onFormatData)
        self.format_button.Disable()
        format_hsizer_3.Add(self.format_button)
        format_sizer.Add(format_hsizer_3)

        # summary box
        summary_box = wx.StaticBox(self.panel, -1, label='Summary')
        summary_sizer = wx.StaticBoxSizer(summary_box, wx.VERTICAL)
        summary_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        summary_hsizer.AddSpacer(5)
        summary_vsizer = wx.BoxSizer(wx.VERTICAL)
        summary_vsizer.AddSpacer(10)
        self.summary_button = wx.Button(self.panel, label = "Create Summary Sheet")
        self.summary_button.Bind(event=wx.EVT_BUTTON, handler=self.onSummarySheet)
        self.summary_button.Disable()
        summary_vsizer.Add(self.summary_button)
        summary_hsizer.Add(summary_vsizer)
        summary_sizer.Add(summary_hsizer, 0)

        # Split left panel horizontally
        self.panel2 = LettersGridPanel(LeftSplitter)
        LeftSplitter.SplitHorizontally(self.panel, self.panel2)
        LeftSplitter.SetSashGravity(0.5)

        #main sizer control
        inner_sizer = wx.BoxSizer(wx.VERTICAL)
        inner_sizer.AddSpacer(20)
        inner_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        inner_hsizer.AddSpacer(10)
        # add selection box
        inner_sizer.Add(selection_sizer, 1, wx.ALL | wx.EXPAND, 10)
        inner_sizer.Add(format_sizer, 1, wx.ALL | wx.EXPAND, 10)
        inner_sizer.Add(summary_sizer, 1, wx.ALL | wx.EXPAND, 10)

        self.panel.SetSizer(inner_sizer) 

        # RHS hold panel
        self.panelRight = HoldPanel(topSplitter)
        topSplitter.SplitVertically(LeftSplitter, self.panelRight)
        topSplitter.SetSashGravity(0.26)
        topSplitter.SetMinimumPaneSize(1)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(topSplitter, 1, wx.EXPAND)
        self.SetSizer(sizer)


    def onSaveLoc(self, event):
        """Select the location to save the results.
        
        + Will create required folder structure and blank files
        + button disabled after use
        + select data button enabled
        """
        self.browse_save_loc.Disable()
        self.browse_button.Enable()

        SaveLoc_dialog = wx.DirDialog(self, "Select Save Location", style=wx.DD_DEFAULT_STYLE)
        if SaveLoc_dialog.ShowModal() == wx.ID_CANCEL:
            return None
        
        self.SaveLoc = SaveLoc_dialog.GetPath() + '/'

        # Create Empty files for later fill
        if os.path.exists(self.SaveLoc + 'Plots') == False:
            os.mkdir(self.SaveLoc + 'Plots')
            os.mkdir(self.SaveLoc + 'Plots/Process_Violin_Plots')
            os.mkdir(self.SaveLoc + 'Plots/Capacity')
            os.mkdir(self.SaveLoc + 'Plots/Simulation')
            os.mkdir(self.SaveLoc + 'Plots/Simulation/Trials')
            os.mkdir(self.SaveLoc + 'Plots/Summary')
        if os.path.exists(self.SaveLoc + 'Network_diagrams') == False:
            os.mkdir(self.SaveLoc + 'Network_diagrams')
        initial_files = pd.DataFrame([])
        with pd.ExcelWriter(self.SaveLoc + 'Raw_Sim_Results.xlsx', mode='w') as writer:
            initial_files.to_excel(writer, 'Blank')
        with pd.ExcelWriter(self.SaveLoc + 'Clustering_Transition_Matrix.xlsx', mode='w') as writer:
            initial_files.to_excel(writer, 'Blank')
        with pd.ExcelWriter(self.SaveLoc + 'Process_Centroids.xlsx', mode='w') as writer:
            initial_files.to_excel(writer, 'Set_medoids')
        with pd.ExcelWriter(self.SaveLoc + 'Cluster_Centroids.xlsx', mode='w') as writer:
            initial_files.to_excel(writer, 'Set_medoids')
        with pd.ExcelWriter(self.SaveLoc + 'Simulation_Difference_Matrix.xlsx', mode='w') as writer:
            initial_files.to_excel(writer, 'Blank')

    def onSelectData(self, event):
        """Select the data to use.
        
        + file explorer will only show xlsx files
        + fill the format choice boxes
        + enables column and format button
        """
        wildcard = "EXCEL files (*.xlsx)|*.xlsx"
        select_data_dialog = wx.FileDialog(self, "Open Excel File", wildcard=wildcard,
                               style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if select_data_dialog.ShowModal() == wx.ID_CANCEL:
            return None

        self.data_name = select_data_dialog.GetPath().split('\\')[-1]
        self.data = pd.read_excel(select_data_dialog.GetPath())
        self.data = self.data.replace(' ', np.NaN)

        all_columns = [column for column in self.data.columns]
        self.id_choice.Clear()
        self.activity_choice.Clear()
        self.dates_choice.Clear()
        self.id_choice.AppendItems(all_columns)
        self.activity_choice.AppendItems(all_columns)
        self.dates_choice.AppendItems(all_columns)

        self.columns_button.Enable()
        self.format_button.Enable()
    

    def onFormatData(self, event):
        """Gets main infomration used from data.
        
        + Formats long data into wide.
        + Adds additional inormation to data i.e. pathways
        + Creates initial results tables T1, T2, T3, T4 with results from raw data
        + Fills Left Bottom grid with codes and names
        """
        self.running_format_text.SetLabel('Please wait...')
        id_column = self.id_choice.GetString(self.id_choice.GetCurrentSelection())
        activity_column = self.activity_choice.GetString(self.activity_choice.GetCurrentSelection())
        dates_column = self.dates_choice.GetString(self.dates_choice.GetCurrentSelection())

        self.data, self.df, self.activity_codes, self.multi_activity_codes, self.headers, self.letters, self.multi_letters = Functions.Create_multi_pathways_data(self.data, id_column, activity_column, dates_column, None, None, self.SaveLoc, self.data_name) 

        # fill grid
        num_rows = self.panel2.LettersGrid.GetNumberRows()
        if num_rows != 0:
            self.panel2.LettersGrid.DeleteRows(pos=0, numRows=num_rows, updateLabels=True)
        self.panel2.LettersGrid.AppendRows(numRows=len(self.activity_codes))
        for k, v in enumerate(self.activity_codes.values()):
            self.panel2.LettersGrid.SetCellValue(k,0,str(v))
        for k, v in enumerate(self.activity_codes.keys()):
            self.panel2.LettersGrid.SetCellValue(k,1,str(v))  
        
        self.panel2.LettersGrid.AutoSizeColumns(setAsMin=True)

        attr = gridlib.GridCellAttr()
        attr.SetReadOnly(True)
        for row in range(len(self.activity_codes)):
            self.panel2.LettersGrid.SetRowAttr(row, attr.Clone())

        # Create initial results tables
        self.original_name = 'original_formatted'
        self.dataframe_T1, self.dataframe_T2, self.dataframe_T3, self.dataframe_T4, self.original_transitions = Functions.initialise_results_tables(self.data, self.letters)
        initial_individuals, real_last_arrival, self.initial_overall_period = Functions.initial_vis_inputs(self.data, self.headers, self.multi_activity_codes, formatted=True)
        self.dataframe_T1, self.dataframe_T2, self.dataframe_T3, self.dataframe_T4 = Functions.get_vis_summary(self.data, 'totaltime', 'pathways', self.letters, self.letters, 
                                                                                self.dataframe_T1, self.dataframe_T2, self.dataframe_T3, self.dataframe_T4, 
                                                                                self.original_transitions, self.original_transitions, 
                                                                                self.activity_codes, self.target, initial_individuals, 
                                                                                self.SaveLoc, self.original_name, listed_times=True, 
                                                                                last_arrival=real_last_arrival, period=self.initial_overall_period)
        # confirmation message
        self.running_format_text.SetLabel('                                            ')     
        self.summary_button.Enable()
        Info_message = wx.MessageBox(parent=None, message = 'The patient pathways data has been saved to the selected location', caption='Information',style= wx.OK)


    def getonHeaders(self, data):
        """Gets main infomration used from data.
        
        + Dialog choice box to select columns required
        + If group codes selected - will group columns with same name differing by _value - to allow for multiples of same activity
        + Adds additional inormation to data i.e. pathways
        + Creates initial results tables T1, T2, T3, T4 with results from raw data
        + Fills Left Bottom grid with codes and names
        """
        def onHeaders(event):
            columns = self.data.columns
            box = wx.MultiChoiceDialog(self, '', 'Select Columns', columns)
            box_select_all_button = wx.Button(box, label='Select all', pos=(10,10))
            box_select_all_button.Bind(event=wx.EVT_BUTTON, handler=self.onSelectAll(box, columns))
            Group_codes = wx.CheckBox(box, pos=(115,20))
            Group_codes_text = wx.StaticText(box, label='Group Codes', pos=(135,20))


            if box.ShowModal() == wx.ID_OK:
                self.running_text.SetLabel('Please wait...')
                selected = box.GetSelections()

                if Group_codes.IsChecked() == True:
                    # If group codes selected - will group columns with same name differing by _value - to allow for multiples of same activity
                    self.data, self.df, self.activity_codes, self.multi_activity_codes, self.headers, self.letters, self.multi_letters = Functions.Create_multi_pathways_data(self.data, None, None, None, columns, selected,self.SaveLoc, self.data_name) 
                    # Create initial results tables
                    self.original_name = 'original_formatted'
                    self.dataframe_T1, self.dataframe_T2, self.dataframe_T3, self.dataframe_T4, self.original_transitions = Functions.initialise_results_tables(self.data, self.letters)
                    initial_individuals, real_last_arrival, self.initial_overall_period = Functions.initial_vis_inputs(self.data, self.headers, self.multi_activity_codes, formatted=True)
                    self.dataframe_T1, self.dataframe_T2, self.dataframe_T3, self.dataframe_T4 = Functions.get_vis_summary(self.data, 'totaltime', 'pathways', self.letters, self.letters, 
                                                                                            self.dataframe_T1, self.dataframe_T2, self.dataframe_T3, self.dataframe_T4, 
                                                                                            self.original_transitions, self.original_transitions, 
                                                                                            self.activity_codes, self.target, initial_individuals, 
                                                                                            self.SaveLoc, self.original_name, listed_times=True, 
                                                                                            last_arrival=real_last_arrival, period=self.initial_overall_period)

                else:
                    # Standard formation of information
                    self.headers = Functions.onHeaders_selection(columns, selected)
                    self.letters, self.activity_codes = Functions.create_codes(self.headers)
                    self.multi_activity_codes = []
                    self.data, self.df = Functions.Create_pathways_data(self.activity_codes, self.data, self.SaveLoc, self.data_name)      
                    # Create initial results tables
                    self.original_name = 'original'
                    self.dataframe_T1, self.dataframe_T2, self.dataframe_T3, self.dataframe_T4, self.original_transitions = Functions.initialise_results_tables(self.data, self.letters)
                    initial_individuals, real_last_arrival, self.initial_overall_period = Functions.initial_vis_inputs(self.data, self.headers, self.activity_codes, formatted=False)
                    self.dataframe_T1, self.dataframe_T2, self.dataframe_T3, self.dataframe_T4 = Functions.get_vis_summary(self.data, 'totaltime', 'pathways', self.letters, self.letters, 
                                                                                            self.dataframe_T1, self.dataframe_T2, self.dataframe_T3, self.dataframe_T4, 
                                                                                            self.original_transitions, self.original_transitions, 
                                                                                            self.activity_codes, self.target, initial_individuals, 
                                                                                            self.SaveLoc, self.original_name, listed_times=False, 
                                                                                            last_arrival=real_last_arrival, period=self.initial_overall_period)     

                # fill grid
                num_rows = self.panel2.LettersGrid.GetNumberRows()
                if num_rows != 0:
                    self.panel2.LettersGrid.DeleteRows(pos=0, numRows=num_rows, updateLabels=True)
                self.panel2.LettersGrid.AppendRows(numRows=len(self.activity_codes))
                for k, v in enumerate(self.activity_codes.values()):
                    self.panel2.LettersGrid.SetCellValue(k,0,str(v))
                for k, v in enumerate(self.activity_codes.keys()):
                    self.panel2.LettersGrid.SetCellValue(k,1,str(v))  
                
                self.panel2.LettersGrid.AutoSizeColumns(setAsMin=True)

                attr = gridlib.GridCellAttr()
                attr.SetReadOnly(True)
                for row in range(len(self.activity_codes)):
                    self.panel2.LettersGrid.SetRowAttr(row, attr.Clone())

                # confimation message  
                self.running_text.SetLabel('                                            ')     
                self.summary_button.Enable()
                Info_message = wx.MessageBox(parent=None, message = 'The patient pathways data has been saved to the selected location', caption='Information',style= wx.OK)
            event.Skip()
        return onHeaders


    def onSelectAll(self, box, columns):
        """Allows easy selection of all columns listed in dialog choice box."""
        def selectall(event):
            all_selected = [i for i in range(len(columns))]
            box.SetSelections(all_selected)
        return selectall


    def onSummarySheet(self, event):
        """Creates summary word document of input data."""
        Functions.Create_Summary_Sheet(self.data, self.df, self.activity_codes, self.SaveLoc, self.original_name)
        Info_message = wx.MessageBox(parent=None, message = 'The summary sheet has been saved to the selected folder', caption='Information',style= wx.OK)


class LettersGridPanel(wx.Panel):
    """Grid panel for letter codes and activities chosen."""
    def __init__(self, parent):
        """Initialise empty grid with column headers."""
        wx.Panel.__init__(self, parent=parent)  
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.LettersGrid = gridlib.Grid(self)
        self.LettersGrid.CreateGrid(0,2)
        self.LettersGrid.SetColLabelValue(0, 'Name')
        self.LettersGrid.SetColLabelValue(1, 'Code')
        sizer.Add(self.LettersGrid, 1, wx.EXPAND | wx.ALL)

        self.SetSizer(sizer)



#============== Clustering Panel ===============
class RankingsPanel(scrolled.ScrolledPanel):
    """Creates a scrolled panel."""
    def __init__(self, parent, DataPanel):
        """Empty panel for rankings options to be appended."""
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour(wx.Colour(250, 135, 72))
        self.DataPanel = DataPanel


    def onCalcRankings(self, dict_rank_choices):
        """Creates dictionay of rankings - either default or user specified in choice boxes."""
        def CalcRankings(event):
            self.dict_rank = {}            
            if self.default_rank_Y.IsChecked() == True:
                self.dict_rank = self.default_rank
            else:
                for index in self.DataPanel.activity_codes.keys():
                    self.dict_rank[index] = dict_rank_choices[index].GetSelection()
        return CalcRankings


    def onSetupModNW(self, event):   
        """Sets up rankings panel with choice box and default value for each activity."""
        if self.DataPanel.activity_codes != {}:     
            # allows for scrolling
            self.SetupScrolling()
            # setup choices avaliable
            rank_choices = [str(x) for x in range(len(self.DataPanel.activity_codes))]

            Rankings_box = wx.StaticBox(self, -1, label='Rankings')
            Rankings_sizer = wx.StaticBoxSizer(Rankings_box, wx.VERTICAL)
            Rankings_hsizer = wx.BoxSizer(wx.HORIZONTAL)
            Rankings_hsizer.AddSpacer(5)
            Rankings_vsizer = wx.BoxSizer(wx.VERTICAL)
            Rankings_vsizer.AddSpacer(30)

            # Attach and space activity names
            for name in self.DataPanel.activity_codes.values():
                headers_text = wx.StaticText(self, wx.ID_ANY, label=name)
                Rankings_vsizer.Add(headers_text)
                Rankings_vsizer.AddSpacer(30)

            Rankings_vsizer.AddSpacer(30)   
            rank_complete_Text = wx.StaticText(self, id=wx.ID_ANY, label='When finished, click Done')
            Rankings_vsizer.Add(rank_complete_Text)
            Rankings_vsizer.AddSpacer(20)   

            Rankings_hsizer.Add(Rankings_vsizer)
            Rankings_hsizer.AddSpacer(10)

            Rankings_vsizer = wx.BoxSizer(wx.VERTICAL)
            Rankings_vsizer.AddSpacer(30)
            dict_rank_choices = {}
            for index, name in self.DataPanel.activity_codes.items():
                dict_rank_choices[index] = wx.Choice(self, choices=rank_choices)
                Rankings_vsizer.Add(dict_rank_choices[index])
                Rankings_vsizer.AddSpacer(22.5)

            Rankings_vsizer.AddSpacer(35)   
            rank_complete = wx.Button(parent=self, label = "Done")
            rank_complete.Bind(event=wx.EVT_BUTTON, handler=self.onCalcRankings(dict_rank_choices))
            Rankings_vsizer.Add(rank_complete)
            Rankings_vsizer.AddSpacer(20)   

            Rankings_hsizer.Add(Rankings_vsizer)

            Rankings_vsizer = wx.BoxSizer(wx.VERTICAL)
            Rankings_vsizer.AddSpacer(5)
            self.default_rank_Y = wx.CheckBox(parent=self)
            Rankings_vsizer.Add(self.default_rank_Y)            
            
            Rankings_hsizer.Add(Rankings_vsizer)

            Rankings_vsizer = wx.BoxSizer(wx.VERTICAL)
            Rankings_vsizer.AddSpacer(5)
            use_default_rank_text = wx.StaticText(self, id=wx.ID_ANY, label="Default")
            Rankings_vsizer.Add(use_default_rank_text)
            
            self.default_rank = Functions.Get_default_ranks(self.DataPanel.activity_codes,self.DataPanel.data.pathways)
            for index, name in self.DataPanel.activity_codes.items():
                default_rank_text = wx.StaticText(self, wx.ID_ANY, str(self.default_rank[index]))
                Rankings_vsizer.Add(default_rank_text)
                Rankings_vsizer.AddSpacer(30)

            Rankings_hsizer.Add(Rankings_vsizer)
            Rankings_sizer.Add(Rankings_hsizer, 0)


            # main sizer control
            main_sizer = wx.BoxSizer(wx.VERTICAL)
            main_hsizer = wx.BoxSizer(wx.HORIZONTAL)
            main_hsizer.AddSpacer(10)
            main_vsizer = wx.BoxSizer(wx.VERTICAL)
            main_vsizer.AddSpacer(20)
            # add Mod NW Note
            note_text = wx.StaticText(self, wx.ID_ANY, label='Note: Only used with Modified Needleman-Wunsch Metric')
            main_vsizer.Add(note_text)
            main_hsizer.Add(main_vsizer)
            # add box
            main_sizer.Add(main_hsizer)
            main_sizer.Add(Rankings_sizer, 1, wx.ALL | wx.EXPAND, 10)

            self.SetSizer(main_sizer) 
            event.Skip()
        

class GroupingsPanel(scrolled.ScrolledPanel):
    """Creates a scrolled panel."""
    def __init__(self, parent, DataPanel):
        """Empty panel for groupings options to be appended."""
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour(wx.Colour(250, 135, 72))
        self.DataPanel = DataPanel     


    def onCalcGroupings(self, dict_choices_group):
        """Creates dictionay of group selected."""
        def CalcGroupings(event):
            self.dict_group = {}
            for index in self.DataPanel.activity_codes.keys():
                self.dict_group[index] = dict_choices_group[index].GetSelection()
        return CalcGroupings


    def onSetupModNW(self, event):    
        """Sets up groupings panel with choice box for each activity."""  
        if self.DataPanel.activity_codes != {}:
            # allows for scrolling
            self.SetupScrolling()
            # setup choices avaliable
            group_choices = ['Group ' + str(x) for x in range(len(self.DataPanel.activity_codes))]

            Groupings_box = wx.StaticBox(self, -1, label='Groupings')
            Groupings_sizer = wx.StaticBoxSizer(Groupings_box, wx.VERTICAL)
            Groupings_hsizer = wx.BoxSizer(wx.HORIZONTAL)
            Groupings_hsizer.AddSpacer(5)
            Groupings_vsizer = wx.BoxSizer(wx.VERTICAL)
            Groupings_vsizer.AddSpacer(10)

            # Attach and space activity names
            for name in self.DataPanel.activity_codes.values():
                headers_text = wx.StaticText(self, wx.ID_ANY, label=name)
                Groupings_vsizer.Add(headers_text)
                Groupings_vsizer.AddSpacer(30)

            Groupings_vsizer.AddSpacer(20)
            group_complete_Text = wx.StaticText(self, id=wx.ID_ANY, label='When finished, click Done')
            Groupings_vsizer.Add(group_complete_Text)
            Groupings_vsizer.AddSpacer(20)

            Groupings_hsizer.Add(Groupings_vsizer)
            Groupings_hsizer.AddSpacer(75)
            
            Groupings_vsizer = wx.BoxSizer(wx.VERTICAL)
            Groupings_vsizer.AddSpacer(10)
            dict_choices_group = {}
            for index, name in self.DataPanel.activity_codes.items():
                dict_choices_group[index] = wx.Choice(self, choices=group_choices)
                dict_choices_group[index].SetSelection(0)
                Groupings_vsizer.Add(dict_choices_group[index])
                Groupings_vsizer.AddSpacer(22.5)

            Groupings_vsizer.AddSpacer(20)
            group_complete = wx.Button(parent=self, label = "Done")
            group_complete.Bind(event=wx.EVT_BUTTON, handler=self.onCalcGroupings(dict_choices_group))
            Groupings_vsizer.Add(group_complete)
            Groupings_vsizer.AddSpacer(20)

            Groupings_hsizer.Add(Groupings_vsizer)
            Groupings_sizer.Add(Groupings_hsizer, 0)

            # main sizer control
            main_sizer = wx.BoxSizer(wx.VERTICAL)
            main_sizer.AddSpacer(20)
            main_hsizer = wx.BoxSizer(wx.HORIZONTAL)
            main_hsizer.AddSpacer(10)
            # add note text
            note_text = wx.StaticText(self, wx.ID_ANY, label='Note: Only used with Modified Needleman-Wunsch Metric')
            main_hsizer.Add(note_text)
            main_sizer.Add(main_hsizer)
            # add box
            main_sizer.Add(Groupings_sizer, 1, wx.ALL | wx.EXPAND, 10)

            self.SetSizer(main_sizer)      
            event.Skip()


class MatrixThread(Thread):
    """Thread for calculating distance matrix."""
    def __init__(self, ClusteringPanel, DataPanel, RankingsPanel, GroupingsPanel, requestQ, resultQ):
        Thread.__init__(self)
        """Initialise thread."""
        self.ClusteringPanel = ClusteringPanel
        self.DataPanel = DataPanel
        self.RankingsPanel = RankingsPanel
        self.GroupingsPanel = GroupingsPanel
        self.requestQ = requestQ
        self.resultQ= resultQ
        self.start()

        self.metrics = {0: textdistance.levenshtein.distance,
                   1: textdistance.damerau_levenshtein.distance,
                   2: textdistance.jaro.distance,
                   3: textdistance.jaro_winkler.distance,
                   4: textdistance.needleman_wunsch.distance,
                   5: textdistance.Jaccard(qval=2).distance,
                   6: textdistance.Cosine(qval=2).distance,
                   7: textdistance.lcsstr.distance,
                   8: 'ModNW'}
    
    def run(self):
        """Calculate the distance matrix from choice of metric."""
        if self.ClusteringPanel.Metric_type.GetCurrentSelection() == 8:
            Weights = Functions.Get_Weights(self.RankingsPanel.dict_rank) 
        # without try attribute error occurs on start up
        try:
            # create empty matrix
            self.dist_matrix = [[0 for i in range(len(self.DataPanel.df.pathway))] for j in range(len(self.DataPanel.df.pathway))]
            self.requestQ.put(self.dist_matrix)
            for i in range(len(self.DataPanel.df.pathway)):
                for j in range(len(self.DataPanel.df.pathway)):
                    if self.ClusteringPanel.Metric_type.GetCurrentSelection() == 8:
                        self.dist_matrix[i][j] = algo.Mod_NW(self.DataPanel.df.pathway[i],
                                                            self.DataPanel.df.pathway[j],
                                                            self.ClusteringPanel.g,
                                                            self.ClusteringPanel.m,
                                                            self.ClusteringPanel.s,
                                                            self.ClusteringPanel.ns,
                                                            Weights,
                                                            self.GroupingsPanel.dict_group)
                    else:
                        self.dist_matrix[i][j] = self.metrics[self.ClusteringPanel.Metric_type.GetCurrentSelection()](self.DataPanel.df.pathway[i],
                                                                                                                self.DataPanel.df.pathway[j])
                # pause in between updates for progress bar
                time.sleep(0.01)            
                wx.CallAfter(pub.sendMessage, "update", msg="")
            # returns the result
            self.resultQ.put(self.dist_matrix)
        except AttributeError:
            pass


class MyProgressDialog(wx.Dialog):
    """Progress bar dialog box."""
    def __init__(self, DataPanel):      
        wx.Dialog.__init__(self,None,title="Calculating Matrix")
        """Initialies progress bar dialog."""
        self.DataPanel = DataPanel  
        self.count = 0
        # Set the length of the progress bar to number in df
        self.progress = wx.Gauge(self, range=len(self.DataPanel.df.pathway))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.progress,0,wx.EXPAND)
        self.SetSizer(sizer)
        # subscribe to updates
        pub.subscribe(self.updateProgress,"update")
    

    def updateProgress(self, msg):
        """Update the progress bar with calculation, increase by 1."""
        # Can be improved by increasing by number passed since last time
        self.count += 1
        # close window on completion
        if self.count >= len(self.DataPanel.df.pathway):
            self.Destroy()
        self.progress.SetValue(self.count)


class ClusteringPanel(wx.Panel):
    """Clustering Panel."""
    def __init__(self, parent, DataPanel, MainClusteringPanel, RankingsPanel, GroupingsPanel, requestQ, resultQ):
        """Set up the clustering panel layout."""
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour(wx.Colour(250, 135, 72))
        self.parent = parent
        self.DataPanel = DataPanel
        self.MainClusteringPanel = MainClusteringPanel
        self.RankingsPanel = RankingsPanel
        self.GroupingsPanel = GroupingsPanel
        # needed for threading
        self.requestQ = requestQ
        self.resultQ= resultQ
        self.comp_Matrix = [[]]
        self.initial_medoids_dict = {'Choose Previous': []}
        self.set_medoids = []
        self.set_no = 0

        # Modified Needleman-Wunsch box
        Modified_box = wx.StaticBox(self, -1, label='Modified Needleman-Wunsch')
        Modified_sizer = wx.StaticBoxSizer(Modified_box, wx.VERTICAL)
        Modified_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        Modified_hsizer.AddSpacer(5)
        Modified_vsizer = wx.BoxSizer(wx.VERTICAL)
        metric_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        metric_hsizer.AddSpacer(5)
        update_button = wx.Button(parent=self, label='Set Rankings and Groupings')
        update_button.Bind(event=wx.EVT_BUTTON, handler=self.RankingsPanel.onSetupModNW)
        update_button.Bind(event=wx.EVT_BUTTON, handler=self.GroupingsPanel.onSetupModNW)
        metric_hsizer.Add(update_button)
        Modified_vsizer.Add(metric_hsizer)
        Modified_vsizer.AddSpacer(20)
        def_algo = wx.StaticText(self, id=wx.ID_ANY, label='Select modified Needleman-Wunsch penalty values:')
        Modified_vsizer.Add(def_algo)
        Modified_vsizer.AddSpacer(10)
        gap_text = wx.StaticText(self, id=wx.ID_ANY, label="Gap = ")
        Modified_hsizer.Add(gap_text)     
        Modified_hsizer.AddSpacer(10)  
        self.g_var_spin = wx.SpinCtrl(self, wx.ID_ANY, value='2', min=0, max=100, size =(40,20))
        Modified_hsizer.Add(self.g_var_spin)
        Modified_hsizer.AddSpacer(10)
        swap_text = wx.StaticText(self, id=wx.ID_ANY, label="Swap = ")
        Modified_hsizer.Add(swap_text)       
        Modified_hsizer.AddSpacer(10)    
        self.s_var_spin = wx.SpinCtrl(self, wx.ID_ANY, value='2', min=0, max=100, size =(40,20))
        Modified_hsizer.Add(self.s_var_spin)   
        Modified_hsizer.AddSpacer(10)
        noswap_text = wx.StaticText(self, id=wx.ID_ANY, label="No-Swap = ")
        Modified_hsizer.Add(noswap_text)     
        Modified_hsizer.AddSpacer(10)  
        self.ns_var_spin = wx.SpinCtrl(self, wx.ID_ANY, value='5', min=0, max=100, size =(40,20))
        Modified_hsizer.Add(self.ns_var_spin)
        Modified_vsizer.Add(Modified_hsizer)
        Modified_vsizer.AddSpacer(20)
        Modified_sizer.Add(Modified_vsizer)
        Modified_sizer.AddSpacer(5)

        # Distance Matrix
        Matrix_box = wx.StaticBox(self, -1, label='Distance Matrix')
        Matrix_sizer = wx.StaticBoxSizer(Matrix_box, wx.VERTICAL)
        Matrix_sizer.AddSpacer(10)
        Matrix_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        Matrix_hsizer.AddSpacer(5)
        self.Metric_type = wx.Choice(self,
             choices=['Levenshtein',
                    'Damerau-Levenshtein',
                    'Jaro', 
                    'Jaro-Winkler', 
                    'Needlean-Wunsch', 
                    'Jaccard',
                    'Cosine',
                    'Longest Common Subsequence',
                    'Modified Needleman-Wunsch'])
        self.Metric_type.SetSelection(0)
        Matrix_hsizer.Add(self.Metric_type)
        Matrix_hsizer.AddSpacer(90)
        create_matrix = wx.Button(parent=self, label = "Create Matrix")
        create_matrix.Bind(event=wx.EVT_BUTTON, handler=self.onMatrixButton)
        Matrix_hsizer.Add(create_matrix)
        Matrix_sizer.Add(Matrix_hsizer)
        Matrix_sizer.AddSpacer(5)


        # Cluster box
        Cluster_box = wx.StaticBox(self, -1, label='Cluster')
        Cluster_sizer = wx.StaticBoxSizer(Cluster_box, wx.VERTICAL)

        Centroids_box = wx.StaticBox(self, -1, label='Centroids')
        Centroids_sizer = wx.StaticBoxSizer(Centroids_box, wx.VERTICAL)
        Centroids_hsizer = wx.BoxSizer(wx.HORIZONTAL)  
        self.select_medoids = wx.CheckListBox(parent=self, choices=['Random', 'Most Occured', 'Least Distance', 'Specify', 'Previous'])
        self.select_medoids.Bind(event=wx.EVT_CHECKLISTBOX, handler=self.onMultipleSelect)
        Centroids_hsizer.Add(self.select_medoids)
        Centroids_hsizer.AddSpacer(10)
        seperator_line = wx.StaticLine(self, id=wx.ID_ANY, size=(1, 80), style=wx.LI_VERTICAL)
        Centroids_hsizer.Add(seperator_line)
        Centroids_hsizer.AddSpacer(10)
        Centroids_vsizer_2 = wx.BoxSizer(wx.VERTICAL)  
        Centroids_vsizer_2.AddSpacer(20)
        self.Specify_textbox = wx.TextCtrl(parent=self, value= 'Specify e.g. 0,1,2,3')
        Centroids_vsizer_2.Add(self.Specify_textbox)
        Centroids_vsizer_2.AddSpacer(10)
        self.previous_sets = ['Choose Previous']
        self.previous_choice = wx.Choice(parent=self, choices=self.previous_sets)
        self.previous_choice.SetSelection(0)
        Centroids_vsizer_2.Add(self.previous_choice)
        Centroids_hsizer.Add(Centroids_vsizer_2)
        Centroids_sizer.Add(Centroids_hsizer)

        Cluster_sizer.Add(Centroids_sizer)
        Cluster_sizer.AddSpacer(10)

        Results_box = wx.StaticBox(self, -1, label='Results')
        Results_sizer = wx.StaticBoxSizer(Results_box, wx.VERTICAL)
        Results_hsizer = wx.BoxSizer(wx.HORIZONTAL)  
        self.result_type = wx.CheckListBox(parent=self, choices=['All','Best k','Best k (ex 2)','k only'])
        self.result_type.Bind(event=wx.EVT_CHECKLISTBOX, handler=self.onMultipleSelect)
        Results_hsizer.Add(self.result_type)
        Results_hsizer.AddSpacer(10)
        seperator_line = wx.StaticLine(self, id=wx.ID_ANY, size=(1, 80), style=wx.LI_VERTICAL)
        Results_hsizer.Add(seperator_line)
        Results_hsizer.AddSpacer(10)
        Results_vsizer_2 = wx.BoxSizer(wx.VERTICAL)  
        select_max_k_text = wx.StaticText(self, wx.ID_ANY, 'Maximum value for k')
        Results_vsizer_2.Add(select_max_k_text)
        Results_vsizer_2.AddSpacer(20)
        self.select_max_k = wx.SpinCtrl(self, wx.ID_ANY, value='2', min=2, max=100, size= (50, 25))
        Results_vsizer_2.Add(self.select_max_k)
        Results_hsizer.Add(Results_vsizer_2)
        Results_hsizer.AddSpacer(10)
        Results_sizer.Add(Results_hsizer)

        Cluster_sizer.Add(Results_sizer)
        Cluster_sizer.AddSpacer(10)

        Centroids_hsizer2_5 = wx.BoxSizer(wx.HORIZONTAL)  
        select_adjust_text = wx.StaticText(self, wx.ID_ANY, 'Process based: Adjust percentage')
        Centroids_hsizer2_5.Add(select_adjust_text)
        Centroids_hsizer2_5.AddSpacer(20)
        self.adjust_perc = wx.SpinCtrl(self, wx.ID_ANY, value='5', min=0, max=100, size= (50, 25))
        Centroids_hsizer2_5.Add(self.adjust_perc)
        Cluster_sizer.Add(Centroids_hsizer2_5)
        Cluster_sizer.AddSpacer(10)

        Centroids_hsizer2_5a = wx.BoxSizer(wx.HORIZONTAL)  
        select_tol_text = wx.StaticText(self, wx.ID_ANY, 'Process based: Highlight results within tolerance')
        Centroids_hsizer2_5a.Add(select_tol_text)
        Centroids_hsizer2_5a.AddSpacer(20)
        self.tolerance = wx.SpinCtrl(self, wx.ID_ANY, value='0', min=0, max=100, size= (50, 25))
        Centroids_hsizer2_5a.Add(self.tolerance)
        Cluster_sizer.Add(Centroids_hsizer2_5a)
        Cluster_sizer.AddSpacer(10)

        Centroids_hsizer3 = wx.BoxSizer(wx.HORIZONTAL)          
        include_centroids_text = wx.StaticText(self, id=wx.ID_ANY, label="Save centroids to data", pos=(70,465))
        Centroids_hsizer3.Add(include_centroids_text)
        Centroids_hsizer3.AddSpacer(15)
        self.include_centroids_box = wx.CheckBox(parent=self, pos =(50, 465))
        Centroids_hsizer3.Add(self.include_centroids_box)
        Cluster_sizer.Add(Centroids_hsizer3)
        Cluster_sizer.AddSpacer(10)
        
        Centroids_hsizer4 = wx.BoxSizer(wx.HORIZONTAL)
        self.create_cluster = wx.Button(parent=self, label = "Classic Cluster")
        self.create_cluster.Bind(event=wx.EVT_BUTTON, handler=self.onClustering)
        self.create_cluster.Disable()
        Centroids_hsizer4.Add(self.create_cluster)
        Centroids_hsizer4.AddSpacer(150)
        self.create_process_based = wx.Button(parent=self, label = "Process Based Cluster")
        self.create_process_based.Bind(event=wx.EVT_BUTTON, handler=self.onProcessClustering)
        self.create_process_based.Disable()
        Centroids_hsizer4.Add(self.create_process_based)
        Cluster_sizer.Add(Centroids_hsizer4)
        Cluster_sizer.AddSpacer(20)


        # main sizer control
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.AddSpacer(20)
        main_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        main_hsizer.AddSpacer(10)
        # add box
        main_sizer.Add(Modified_sizer, 1, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(Matrix_sizer, 1, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(Cluster_sizer, 1, wx.ALL | wx.EXPAND, 10)


        self.SetSizer(main_sizer) 


    def onMultipleSelect(self,event):
        """Error if multiple boxes selected."""
        if len(self.select_medoids.GetCheckedItems()) > 1 or len(self.result_type.GetCheckedItems()) > 1:
            error_message = wx.MessageBox(parent=None, message = 'Please only select one box. \nIf more than one box ticked, the top most option will be selected.', 
                                        caption='Error',style= wx.OK)
        event.Skip()


    def onMatrixButton(self,event):
        """Calculate distance matrix."""
        self.m = 1
        self.g, self.s, self.ns = self.g_var_spin.GetValue(),self.s_var_spin.GetValue(),self.ns_var_spin.GetValue()

        btn = event.GetEventObject()
        btn.Disable()
        MatrixThread(self, self.DataPanel, self.RankingsPanel, self.GroupingsPanel, self.requestQ, self.resultQ)
        dlg = MyProgressDialog(self.DataPanel)
        dlg.ShowModal()
        btn.Enable()
        # distance matrix
        self.comp_Matrix = self.resultQ.get()
        comp_matrix_df = pd.DataFrame(self.comp_Matrix)

        # save name
        selected_metric = self.Metric_type.GetString(self.Metric_type.GetCurrentSelection())
        if selected_metric == 'Modified Needleman-Wunsch':
            file_name = selected_metric + '_' + str(self.m) + str(self.g) + str(self.s) + str(self.ns) + '.xlsx'
        else:
            file_name = selected_metric + '.xlsx'
        # save
        with pd.ExcelWriter(self.DataPanel.SaveLoc + 'Clustering_Transition_Matrix.xlsx', engine="openpyxl", mode='a') as writer:
            comp_matrix_df.to_excel(writer,file_name)

        # enable clutering buttons
        self.create_cluster.Enable()
        self.create_process_based.Enable()
        
        return self.comp_Matrix


    def clusteringOptions(self):
        """Get user options for clustering."""
        # Define k
        self.max_k = self.select_max_k.GetValue()  
        if self.max_k > len(self.DataPanel.df.pathway):
            error_message = wx.MessageBox(parent=None, message = 'Value of k is invalid. \nPlease select a value of k less than the number of pathways.', 
                                        caption='Error',style= wx.OK)

        # Get medoids
        if len(self.select_medoids.GetCheckedItems()) == 0:
            error_message = wx.MessageBox(parent=None, message = 'Please select an option for the initial medoids.', caption='Error',style= wx.OK)
        if self.select_medoids.GetCheckedStrings()[0] == 'Previous':
            if self.set_medoids != []:
                self.set_medoids = self.initial_medoids_dict[self.previous_choice.GetString(self.previous_choice.GetCurrentSelection())]
                self.specify_medoids = 'No'
            else:
                error_message = wx.MessageBox(parent=None, message = 'Please only select Previous after first selection run', caption='Error',style= wx.OK)        
        else:
            self.set_medoids, self.specify_medoids = Functions.GetMedoids(self.select_medoids, self.DataPanel.df, self.max_k, self.DataPanel.data, self.comp_Matrix, self.Specify_textbox)
            if self.specify_medoids == 'Enter values Error':
                error_message = wx.MessageBox(parent=None, message = 'Please enter the index values.', caption='Error',style= wx.OK)                      
        if len(self.set_medoids) < self.max_k and self.specify_medoids == 'Large Error':
            error_message = wx.MessageBox(parent=None, message = 'Please ensure k is smaller than th number of medoids entered.', caption='Error',style= wx.OK)


        if self.select_medoids.GetCheckedStrings()[0] != 'Previous':
            self.set_no += 1
            set_name = 'Set_' + str(self.set_no)
            self.initial_medoids_dict[set_name] = self.set_medoids
            self.previous_choice.Clear()
            self.previous_choice.AppendItems([str(key) for key in self.initial_medoids_dict.keys()])
            self.previous_choice.SetSelection(0)

        
        medoids_set = [key for key, value in self.initial_medoids_dict.items() if value == self.set_medoids]
        self.save_name = self.Metric_type.GetString(self.Metric_type.GetCurrentSelection()) + '_' + medoids_set[0] + '_'

        # include centroids in data
        if self.include_centroids_box.IsChecked() == True:
            self.include_centroids = 'Yes'
        else:
            self.include_centroids = 'No'

        if self.result_type.GetCheckedStrings()[0] == 'Best k (ex 2)':
            if self.max_k == 2:
                 error_message = wx.MessageBox(parent=None, message = 'Please ensure k is greater than 2.', caption='Error',style= wx.OK)


    def onClustering(self,event):
        """Run classic clustering.
        
        + uses silhouette score to suggest "best"
        + returns cluster asignment for each pathway in df
        """
        self.clusteringOptions()
        # Run Clustering
        self.MainClusteringPanel.clustering_results = Functions.RunClustering(self.DataPanel.data, self.DataPanel.df.pathway, self.comp_Matrix, self.set_medoids, self.max_k, 
                                                     self.DataPanel.SaveLoc, self.save_name, self.result_type.GetCheckedStrings()[0], self.include_centroids)     

        if self.include_centroids_box.IsChecked() == True:
            # save set medoids
            df_setmedoid = pd.DataFrame(columns= ['Set Name', 'Set'])
            for name, sets in self.initial_medoids_dict.items():
                df_setmedoid = df_setmedoid.append(pd.Series([name, sets], index=['Set Name', 'Set']), ignore_index=True)
            workbook = openpyxl.load_workbook(self.DataPanel.SaveLoc + 'Cluster_Centroids.xlsx')
            del workbook['Set_medoids']    
            workbook.save(self.DataPanel.SaveLoc + 'Cluster_Centroids.xlsx')
            with pd.ExcelWriter(self.DataPanel.SaveLoc + 'Cluster_Centroids.xlsx', engine="openpyxl", mode='a') as writer:
                df_setmedoid.to_excel(writer,'Set_medoids')


    def onProcessClustering(self,event):
        """Runs process based clustering. 
        
        + uses difference matrix and number of connections to suggest "best"
        + returns centroids of clusters and the number of pathways assigned
        """
        self.clusteringOptions()
        self.MainClusteringPanel.adjust = self.adjust_perc.GetValue()/100
        tol = self.tolerance.GetValue()
        
        # Run Clustering
        self.MainClusteringPanel.process_k, self.MainClusteringPanel.process_clustering_results, plot_name = Functions.RunProcessClustering(self.DataPanel.data, self.DataPanel.df, self.DataPanel.letters, self.comp_Matrix, self.set_medoids, self.max_k,
                                                     self.DataPanel.SaveLoc, self.save_name,  tol, self.result_type.GetCheckedStrings()[0], self.include_centroids, self.MainClusteringPanel.adjust)
        if plot_name != None:
            self.MainClusteringPanel.plot_names.append(plot_name)

        # save set medoids
        if self.include_centroids_box.IsChecked() == True:
            df_setmedoid = pd.DataFrame(columns= ['Set Name', 'Set'])
            for name, sets in self.initial_medoids_dict.items():
                df_setmedoid = df_setmedoid.append(pd.Series([name, sets], index=['Set Name', 'Set']), ignore_index=True)
            workbook = openpyxl.load_workbook(self.DataPanel.SaveLoc + 'Process_Centroids.xlsx')
            del workbook['Set_medoids']    
            workbook.save(self.DataPanel.SaveLoc + 'Process_Centroids.xlsx')
            with pd.ExcelWriter(self.DataPanel.SaveLoc + 'Process_Centroids.xlsx', engine="openpyxl", mode='a') as writer:
                df_setmedoid.to_excel(writer,'Set_medoids')


#-------------- Clustering Main Panel ---------------
class MainClusteringPanel(wx.Panel):
    """Main clustering tab panel"""
    def __init__(self, parent, DataPanel, requestQ, resultQ):
        """Set up clustering tab with notebook of clustering panels."""
        wx.Panel.__init__(self, parent)
        self.SetBackgroundColour(wx.Colour(240, 240, 240))
        topSplitter = wx.SplitterWindow(self) 
        self.requestQ = requestQ
        self.resultQ= resultQ

        self.plot_names = ['']
        self.clustering_results = []
        self.process_clustering_results = pd.DataFrame()
        self.process_k = 0
        self.adjust = 0.05

        
        # Notebook
        notebook = wx.Notebook(topSplitter)
        self.tabOne_Rankings = RankingsPanel(notebook, DataPanel)
        self.tabTwo_Groupings = GroupingsPanel(notebook, DataPanel)
        tabThree_Clustering = ClusteringPanel(notebook, DataPanel, self, self.tabOne_Rankings, self.tabTwo_Groupings, self.requestQ, self.resultQ)
        notebook.AddPage(tabThree_Clustering, "Clustering")
        notebook.AddPage(self.tabOne_Rankings, "Rankings")
        notebook.AddPage(self.tabTwo_Groupings, "Groupings")
        
        # RHS
        self.panelRight = CanvasFrame(topSplitter, DataPanel, canvasPanel=self, plotParent="Cluster")
        topSplitter.SplitVertically(notebook, self.panelRight)
        topSplitter.SetSashGravity(0.26)
        topSplitter.SetMinimumPaneSize(1)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(topSplitter, 1, wx.EXPAND)
        self.SetSizer(sizer)



#============== Simulation ===============
#-------------- Edit Sim ---------------
class EditSim(wx.Panel):
    """Edit sim panel."""
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        """Set up blank notebook with hold panel - Sim.Pro.Flow logo."""
        self.SetBackgroundColour(wx.Colour(240, 240, 240))

        # Notebook
        self.notebook = wx.Notebook(self)
        self.HoldPage = HoldPanel(self.notebook)
        self.notebook.AddPage(self.HoldPage, "")

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizer(sizer)


class ArrivalsPanel(wx.Panel):
    """Panel for arrivals Grid."""
    def __init__(self, parent, ModelSimPanel):
        wx.Panel.__init__(self, parent)
        """Set up the empty arrivals grid"""
        self.SetBackgroundColour(wx.Colour(250, 135, 72))
        self.ModelSimPanel = ModelSimPanel

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.calculate_arrivals = wx.Button(self, label='Calculate')
        self.calculate_arrivals.Bind(event=wx.EVT_BUTTON, handler=self.onCalculate)

        # arrival period grid
        self.ArrivalPeriodGrid = gridlib.Grid(self)
        self.ArrivalPeriodGrid.CreateGrid(1,2)
        self.ArrivalPeriodGrid.SetColLabelValue(0, 'Auto')
        self.ArrivalPeriodGrid.SetColLabelValue(1, 'Custom')
        self.ArrivalPeriodGrid.SetRowLabelValue(0, 'Individuals')
        self.ArrivalPeriodGrid.SetCellValue(0,0,str(self.ModelSimPanel.original_individuals))
        self.ArrivalPeriodGrid.SetCellBackgroundColour(0,0,wx.Colour(240, 240, 240))
        # set to read only
        attr = gridlib.GridCellAttr()
        attr.SetReadOnly(True)
        self.ArrivalPeriodGrid.SetColAttr(0, attr)

        # arrivals grid
        self.ArrivalsGrid = gridlib.Grid(self)
        self.ArrivalsGrid.CreateGrid(1,1)

        # add grid
        self.sizer.Add(self.calculate_arrivals)
        self.sizer.Add(self.ArrivalPeriodGrid)
        self.sizer.Add(self.ArrivalsGrid, 1, wx.EXPAND | wx.ALL)
        self.SetSizer(self.sizer)

    def onCalculate(self, event):
        if self.ArrivalPeriodGrid.GetCellValue(0, 1) == '':
            error_message = wx.MessageBox(parent=None, message = 'Please enter a value in the custom cell', caption='Error',style= wx.OK)
        else:
            arrivalgrid_columns = [self.ArrivalsGrid.GetColLabelValue(c) for c in range(self.ArrivalsGrid.GetNumberCols())]
            for c, column in enumerate(arrivalgrid_columns):
                if column == 'Individuals':
                    for r in range(self.ArrivalsGrid.GetNumberRows()):
                        calculated_individuals = int(round((int(self.ArrivalsGrid.GetCellValue(r, c)) / self.ModelSimPanel.original_individuals) * int(self.ArrivalPeriodGrid.GetCellValue(0, 1)),0))
                        self.ArrivalsGrid.SetCellValue(r, c+2, str(calculated_individuals))
                        calculated_arrivals = calculated_individuals / self.ModelSimPanel.overall_period
                        self.ArrivalsGrid.SetCellValue(r, c+3, str(calculated_arrivals))


class PathwaysPanel(wx.Panel):
    """Panel for pathways grid."""
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        """Set up the empty pathways grid."""

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.PathwaysGrid = gridlib.Grid(self)
        self.PathwaysGrid.CreateGrid(1,1)
        self.sizer.Add(self.PathwaysGrid, 1, wx.EXPAND | wx.ALL)
        self.SetSizer(self.sizer)


class Custom_ServicePanel(wx.Panel):
    """Service panel for customing service grid."""
    def __init__(self, parent, letters, input_service):
        wx.Panel.__init__(self, parent)
        """Initialise service grid
        
        + Fill with initial values - set to read only
        + Additional columns for editing values
        """
        self.ServiceGrid = gridlib.Grid(self)
        # create grid
        self.ServiceGrid.CreateGrid(len(letters), 4)
        for c in range(4):
            self.ServiceGrid.SetColSize(c, 135)
        # change names
        self.ServiceGrid.SetColLabelValue(0, 'Distribution')
        self.ServiceGrid.SetColLabelValue(1, 'Service Time')
        self.ServiceGrid.SetColLabelValue(2, 'Distribution')
        self.ServiceGrid.SetColLabelValue(3, 'Service Time')
        for index, key in enumerate(letters):
            self.ServiceGrid.SetRowLabelValue(index, key)
        # fill grid
        self.dist_choices = wx.grid.GridCellChoiceEditor(['Deterministic', 'Exponential'], False)
        self.float_choices = wx.grid.GridCellFloatEditor(width=4, precision=2, format=wx.grid.GRID_FLOAT_FORMAT_FIXED)
        for r, dist in enumerate(letters):
            self.ServiceGrid.SetCellValue(r,0,'Deterministic')
            self.ServiceGrid.SetCellBackgroundColour(r,0,wx.Colour(240, 240, 240))
            self.ServiceGrid.SetCellValue(r,1,str(input_service))
            self.ServiceGrid.SetCellBackgroundColour(r,1,wx.Colour(240, 240, 240))
            self.ServiceGrid.SetCellEditor(r, 2, self.dist_choices)   
            self.ServiceGrid.SetCellEditor(r, 3, self.float_choices)   

        # set to read only
        attr = gridlib.GridCellAttr()
        attr.SetReadOnly(True)
        self.ServiceGrid.SetColAttr(0, attr.Clone())
        self.ServiceGrid.SetColAttr(1, attr.Clone())
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.ServiceGrid, 1, wx.EXPAND | wx.ALL)
        self.SetSizer(sizer)


class Custom_CapacityPanel(wx.Panel):
    """Capacity panel for customing initial capacity grid."""
    def __init__(self, parent, ModelSimPanel, SimulationPanel, letters):
        wx.Panel.__init__(self, parent)
        """Capacity panel split into - top: fixed, bottom: custom
        
        + Fill top grid with initial values from data - set to read only
        + Bottom grid empty with options for update, view and clear
        """
        self.ModelSimPanel = ModelSimPanel
        self.SimulationPanel = SimulationPanel
        
        mainSplitter = wx.SplitterWindow(self)

        self.TopPanel = wx.Panel(mainSplitter)
        self.BottomPanel = wx.Panel(mainSplitter)


        sizer = wx.BoxSizer(wx.VERTICAL)
        name_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        # create top grid
        self.TopCapGrid = gridlib.Grid(self.TopPanel)
        self.TopCapGrid.CreateGrid(len(letters), 9)
        for c in range(9):
            self.TopCapGrid.SetColSize(c, 110)
        # labels
        for i, day in enumerate(name_days):
            self.TopCapGrid.SetColLabelValue(i, day)
        self.TopCapGrid.SetColLabelValue(7, 'Work Week Total')
        self.TopCapGrid.SetColLabelValue(8, 'Week Total')
        for index, key in enumerate(letters):
            self.TopCapGrid.SetRowLabelValue(index, key)
        # fill grid
        for r, pattern in enumerate(self.ModelSimPanel.input_servers_capacity.values()):
            for c in range(len(name_days)):
                self.TopCapGrid.SetCellValue(r,c,str(pattern[c]))
            self.TopCapGrid.SetCellValue(r,7,str(sum(pattern[0:5])))
            self.TopCapGrid.SetCellValue(r,8,str(sum(pattern)))
        # set to read only
        attr = gridlib.GridCellAttr()
        attr.SetReadOnly(True)
        for c in range(9):
            self.TopCapGrid.SetColAttr(c, attr)       
        self.TopCapGrid.SetDefaultCellBackgroundColour(wx.Colour(240, 240, 240))  
        sizer.Add(self.TopCapGrid, 1, wx.EXPAND | wx.ALL)   
        self.TopPanel.SetSizer(sizer)


        # bottom panel
        sizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL) 
        self.Update = wx.Button(self.BottomPanel, label='Update')
        self.Update.Bind(wx.EVT_BUTTON, handler=self.onUpdateChoices)
        hsizer.Add(self.Update)   
        hsizer.AddSpacer(10)
        self.capacity_choices = ['Pattern', 'Smoothed']
        self.cap_type = wx.Choice(self.BottomPanel, choices=self.capacity_choices)
        self.cap_type.SetSelection(0)
        hsizer.Add(self.cap_type)
        hsizer.AddSpacer(10)
        self.ViewCalc = wx.Button(self.BottomPanel, label='View')
        self.ViewCalc.Bind(wx.EVT_BUTTON, handler=self.onViewCalc)
        hsizer.Add(self.ViewCalc)   
        hsizer.AddSpacer(10)
        self.resetGrid = wx.Button(self.BottomPanel, label='Clear')
        self.resetGrid.Bind(wx.EVT_BUTTON, handler=self.onResetGrid)
        hsizer.Add(self.resetGrid)  
        sizer.Add(hsizer)
        # create bottom grid
        self.BottomCapGrid = gridlib.Grid(self.BottomPanel)
        self.BottomCapGrid.CreateGrid(len(letters), 7)
        # change names
        for i, day in enumerate(name_days):
            self.BottomCapGrid.SetColSize(i, 110)
            self.BottomCapGrid.SetColLabelValue(i, day)
        for index, key in enumerate(letters):
            self.BottomCapGrid.SetRowLabelValue(index, key)
        sizer.Add(self.BottomCapGrid, 1, wx.EXPAND | wx.ALL)   
        self.BottomPanel.SetSizer(sizer)

        mainSplitter.SplitHorizontally(self.TopPanel, self.BottomPanel)
        mainSplitter.SetSashGravity(0.5)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(mainSplitter, 1, wx.EXPAND | wx.ALL)
        self.SetSizer(sizer)


    def onUpdateChoices(self, event):
        """Update capacity choices avaliable for viewing.
        
        + Default pattern or smoothed
        + Will add additional options from capacity calculation 
        """
        self.cap_type.Clear()
        calculated_cap_names = self.capacity_choices + [name for name in self.SimulationPanel.CalculatedCapacity.keys() if name != 'Initial']
        self.cap_type.AppendItems(calculated_cap_names)
        self.cap_type.SetSelection(0)


    def onViewCalc(self, event):
        """View the capacity pattern selected - avaliable to edit."""
        self.BottomCapGrid.ClearGrid()
        # Either 5 or 7 days for view from basic sim panel option
        days = int(self.ModelSimPanel.time_unit_item.GetString(self.ModelSimPanel.time_unit_item.GetCurrentSelection())[0])
        
        if self.cap_type.GetCurrentSelection() == 0:
            # pattern
            for r, pattern in enumerate(self.ModelSimPanel.input_servers_capacity.values()):
                for c in range(days):
                    self.BottomCapGrid.SetCellValue(r,c,str(pattern[c]))
        elif self.cap_type.GetCurrentSelection() == 1:
            # smoothed
            total_week_cap = [int(self.TopCapGrid.GetCellValue(r,7)) if days == 5 else int(self.TopCapGrid.GetCellValue(r,8)) for r in range(self.BottomCapGrid.GetNumberRows())]
            cap_pattern = [Functions.CreatePattern(week_cap, days) for week_cap in total_week_cap]
            for r, pattern in enumerate(cap_pattern):
                for c in range(days):
                    self.BottomCapGrid.SetCellValue(r,c,str(pattern[c]))
        else:
            # from capacity panel calculation
            calc_cap_name = self.cap_type.GetString(self.cap_type.GetCurrentSelection())
            total_week_cap = self.SimulationPanel.CalculatedPattern[calc_cap_name]
            for r, pattern in enumerate(total_week_cap):
                for c in range(len(pattern)):
                    self.BottomCapGrid.SetCellValue(r,c,str(pattern[c]))


    def onResetGrid(self, event):
        """Clear grid."""
        self.BottomCapGrid.ClearGrid()


class Custom_WarmupPanel(wx.Panel):
    """Warm up panel for customing warm up grid."""
    def __init__(self, parent, dataframe_T4):
        wx.Panel.__init__(self, parent)
        """Initialise warm up grid
        
        + Top of grid for itterative warm up
        + Bottom of grid for warm start
        + Split by merged cell title
        + Additional columns for editing values
        """
        # create grid
        self.WarmupGrid = gridlib.Grid(self)
        self.WarmupGrid.CreateGrid(len(dataframe_T4)+2, 2)
        for c in range(2):
            self.WarmupGrid.SetColSize(c, 135)
        # change names
        self.WarmupGrid.SetColLabelValue(0, 'Default')
        self.WarmupGrid.SetColLabelValue(1, 'Custom')
        self.WarmupGrid.SetRowLabelValue(0, 'Iterations')
        self.WarmupGrid.SetRowLabelValue(1, '')
        for r, key in enumerate(dataframe_T4.iloc[:,0]):
            self.WarmupGrid.SetRowLabelValue(r+2, key)
        # fill grid        
        # iterations
        self.int_choices = wx.grid.GridCellNumberEditor(min=0, max=1000000) 
        self.WarmupGrid.SetCellValue(0,0,'2')
        self.WarmupGrid.SetCellEditor(0,1,self.int_choices)
        self.WarmupGrid.SetCellBackgroundColour(0,0,wx.Colour(240, 240, 240))
        # new heading
        self.WarmupGrid.SetCellSize(1,0,1,2)
        self.WarmupGrid.SetCellBackgroundColour(1,0,wx.Colour(240, 240, 240))
        self.WarmupGrid.SetCellValue(1,0,'    Number of days before active')
        self.WarmupGrid.SetCellFont(1,0,wx.Font(70, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.BOLD))
        # activities
        for r, wait_time in enumerate(dataframe_T4.iloc[:,1]):
            self.WarmupGrid.SetCellValue(r+2,0,str(math.ceil(wait_time)))
            self.WarmupGrid.SetCellBackgroundColour(r+2,0,wx.Colour(240, 240, 240))
            self.WarmupGrid.SetCellEditor(r+2, 1, self.int_choices)   
        self.WarmupGrid.AutoSizeColumns(setAsMin=True)

        # set to read only
        attr = gridlib.GridCellAttr()
        attr.SetReadOnly(True)
        self.WarmupGrid.SetColAttr(0, attr)
        

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.WarmupGrid, 1, wx.EXPAND | wx.ALL)
        self.SetSizer(sizer)


class UtilResultsGrid(wx.Frame):
    """Utilisation results frame."""
    def __init__(self, DataPanel, SimulationPanel):
        wx.Frame.__init__(self, parent=None, title='Simulation Utilisation Results', size=(1300,700))
        """Set up empty utilisation results frame - read only"""
        self.SetBackgroundColour(wx.Colour(240, 240, 240))
        self.DataPanel = DataPanel
        self.SimulationPanel = SimulationPanel

        self.name_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        self.num_setup = 0
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddSpacer(10)

        # top buttons
        util_sizer = wx.BoxSizer(wx.HORIZONTAL)
        util_sizer.AddSpacer(5)
        Title = wx.StaticText(self, label=self.SimulationPanel.tabOne_Setup.current_sim_name + ' - Average Utilisation Percentage')
        util_sizer.Add(Title)
        
        # grid
        self.UtilGrid = gridlib.Grid(self)
        self.UtilGrid.CreateGrid(0,8)
        self.UtilGrid.SetColLabelValue(0, 'Total')
        for c, day in enumerate(self.name_days):
            self.UtilGrid.SetColLabelValue(c+1, day)
        for c in range(8):
            self.UtilGrid.SetColSize(c, 135)

        self.onViewResults()

        sizer.Add(util_sizer)
        sizer.Add(self.UtilGrid, 1, wx.EXPAND | wx.ALL)

        self.SetSizer(sizer)


    def onViewResults(self):        
        # Setup grid
        if self.num_setup == 0:
            self.UtilGrid.AppendRows(len(self.DataPanel.letters))  
        for r, code in enumerate(self.DataPanel.letters):
            self.UtilGrid.SetRowLabelValue(r,code)      
        self.num_setup += 1

        # Fill grid
        for r in range(len(self.DataPanel.letters)):
            for c in range(len(self.SimulationPanel.tabOne_Setup.df_utilisation.columns)):
                self.UtilGrid.SetCellValue(r,c,str(self.SimulationPanel.tabOne_Setup.df_utilisation.iloc[r][c]))

        attr = gridlib.GridCellAttr()
        attr.SetReadOnly(True)
        for row in range(self.UtilGrid.GetNumberRows()):
            self.UtilGrid.SetRowAttr(row, attr.Clone())


#-------------- Sim Panels ---------------
class ModelSimPanel(wx.Panel):
    """Simulation model panel"""
    def __init__(self, parent, DataPanel, MainClusteringPanel, SimulationPanel):
        wx.Panel.__init__(self, parent)
        """Set up the simulation model panel.
        
        Split panel:
        + Left simulation options
        + Right edit sim notebook panel        
        """
        self.SetBackgroundColour(wx.Colour(250, 135, 72))
        self.DataPanel = DataPanel
        self.MainClusteringPanel = MainClusteringPanel
        self.SimulationPanel = SimulationPanel

        self.Arrivals_Dict = {}
        self.Service_Dict = {}
        self.Capacity_Dict = {}
        self.Routing_Dict = {}

        self.current_sim_name = ''
        self.Create_Pages = 0


        # Inputs
        Inputs_box = wx.StaticBox(self, -1, label='Simulation Inputs')
        Inputs_sizer = wx.StaticBoxSizer(Inputs_box, wx.VERTICAL)
        Inputs_sizer.AddSpacer(20)
        
        Inputs_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        Inputs_hsizer.AddSpacer(10)
        arrivals_text = wx.StaticText(self, wx.ID_ANY, label='Arrivals')
        Inputs_hsizer.Add(arrivals_text)
        Inputs_hsizer.AddSpacer(250)        
        self.arrivals_choice = wx.Choice(self, choices=['Auto', 'Custom'])
        self.arrivals_choice.SetSelection(0)
        Inputs_hsizer.Add(self.arrivals_choice)
        Inputs_sizer.Add(Inputs_hsizer, 0)
        Inputs_sizer.AddSpacer(20)

        Inputs_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        Inputs_hsizer.AddSpacer(10)
        service_text = wx.StaticText(self, wx.ID_ANY, label='Service')
        Inputs_hsizer.Add(service_text)
        Inputs_hsizer.AddSpacer(252)        
        self.service_choice = wx.Choice(self, choices=['Auto', 'Custom'])
        self.service_choice.SetSelection(0)
        Inputs_hsizer.Add(self.service_choice)
        Inputs_sizer.Add(Inputs_hsizer, 0)
        Inputs_sizer.AddSpacer(20)

        seperator_line = wx.StaticLine(self, id=wx.ID_ANY, size=(400, 2), style=wx.LI_HORIZONTAL)  
        Inputs_sizer.Add(seperator_line)
        Inputs_sizer.AddSpacer(20)       

        Inputs_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        Inputs_hsizer.AddSpacer(10)
        capacity_text = wx.StaticText(self, wx.ID_ANY, label='Capacity')
        Inputs_hsizer.Add(capacity_text)
        Inputs_hsizer.AddSpacer(245)      
        self.capacity_choice = wx.Choice(self, choices=['Auto', 'Custom'])
        self.capacity_choice.SetSelection(0)
        Inputs_hsizer.Add(self.capacity_choice)
        Inputs_sizer.Add(Inputs_hsizer, 0)
        Inputs_sizer.AddSpacer(20)

        seperator_line = wx.StaticLine(self, id=wx.ID_ANY, size=(400, 2), style=wx.LI_HORIZONTAL)  
        Inputs_sizer.Add(seperator_line)
        Inputs_sizer.AddSpacer(20)       

        Inputs_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        Inputs_hsizer.AddSpacer(10)
        warm_text = wx.StaticText(self, wx.ID_ANY, label='Warm up')
        Inputs_hsizer.Add(warm_text)
        Inputs_hsizer.AddSpacer(105)     
        self.warmup_type = wx.Choice(self, choices=['None', 'Warm Start', 'Itterative'])
        self.warmup_type.SetSelection(0)
        Inputs_hsizer.Add(self.warmup_type)
        Inputs_hsizer.AddSpacer(50)        
        self.warm_choice = wx.Choice(self, choices=['Auto', 'Custom'])
        self.warm_choice.SetSelection(0)
        Inputs_hsizer.Add(self.warm_choice)
        Inputs_sizer.Add(Inputs_hsizer, 0)
        Inputs_sizer.AddSpacer(20)
    
        
        # Time
        time_box = wx.StaticBox(self, -1, label='Time')
        time_sizer = wx.StaticBoxSizer(time_box, wx.VERTICAL)
        time_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        time_hsizer.AddSpacer(10)
        time_vsizer = wx.BoxSizer(wx.VERTICAL)
        time_vsizer.AddSpacer(10)

        time_unit_text = wx.StaticText(self, wx.ID_ANY, label='Week type')
        time_vsizer.Add(time_unit_text)
        time_vsizer.AddSpacer(20)
        time_run_text = wx.StaticText(self, wx.ID_ANY, label='Number of Individuals')
        time_vsizer.Add(time_run_text)
        time_vsizer.AddSpacer(20)
        target_text = wx.StaticText(self, wx.ID_ANY, label='Target Days')
        time_vsizer.Add(target_text)
        time_vsizer.AddSpacer(20)
        time_trials_text = wx.StaticText(self, wx.ID_ANY, label='Number of Trials')
        time_vsizer.Add(time_trials_text)
        time_vsizer.AddSpacer(20)
        time_seed_text = wx.StaticText(self, wx.ID_ANY, label='Simulation Seed')
        time_vsizer.Add(time_seed_text)
        time_vsizer.AddSpacer(15)
        time_hsizer.Add(time_vsizer)
        time_hsizer.AddSpacer(175)

        time_vsizer = wx.BoxSizer(wx.VERTICAL)
        time_vsizer.AddSpacer(10)
        self.time_unit_item = wx.Choice(self, choices=['5 days','7 days'])
        self.time_unit_item.SetSelection(0)
        time_vsizer.Add(self.time_unit_item)
        time_vsizer.AddSpacer(10)
        self.inds_choice = wx.Choice(self, choices=['Auto','Custom'])
        self.inds_choice.SetSelection(0)
        time_vsizer.Add(self.inds_choice)
        time_vsizer.AddSpacer(10)
        self.target_choice = wx.SpinCtrl(self, wx.ID_ANY, value=str(self.DataPanel.target), min=0, max=10000, size =(60,20))
        time_vsizer.Add(self.target_choice)
        time_vsizer.AddSpacer(15)
        self.time_trials = wx.SpinCtrl(self, wx.ID_ANY, value='1', min=1, max=10000, size =(60,20))
        time_vsizer.Add(self.time_trials)
        time_vsizer.AddSpacer(15)
        self.sim_seed_item = wx.SpinCtrl(self, wx.ID_ANY, value='0', min=0, max=10000, size =(60,20))
        time_vsizer.Add(self.sim_seed_item)
        time_vsizer.AddSpacer(15)
        time_hsizer.Add(time_vsizer)
        time_sizer.Add(time_hsizer, 0)
        time_sizer.AddSpacer(10)

        # Network
        network_box = wx.StaticBox(self, -1, label='Network')
        network_sizer = wx.StaticBoxSizer(network_box, wx.VERTICAL)
        network_sizer.AddSpacer(10)
        network_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        network_hsizer.AddSpacer(10)
        self.draw_network_button = wx.Button(parent=self, label = "Draw")
        self.draw_network_button.Bind(event=wx.EVT_BUTTON, handler=self.onDraw)
        self.draw_network_button.Disable()
        network_hsizer.Add(self.draw_network_button)    
        network_hsizer.AddSpacer(10)   
        self.plot_options = []
        self.plot_selection = wx.Choice(self, choices=self.plot_options, size=(200, 25))
        network_hsizer.Add(self.plot_selection)
        network_hsizer.AddSpacer(10)
        self.view_button = wx.Button(self, label='View')
        self.view_button.Bind(event=wx.EVT_BUTTON, handler=self.onViewNetwork)
        network_hsizer.Add(self.view_button)
        network_sizer.Add(network_hsizer, 0)
        network_sizer.AddSpacer(10)

        # Add to panel
        main_box = wx.StaticBox(self, -1, label='')
        main_sizer = wx.StaticBoxSizer(main_box, wx.VERTICAL)
        # add sim type        
        main_sizer.AddSpacer(20)
        self.sim_type = wx.Choice(self, choices=['Raw Pathways', 'Full Transitions', 'Clustered Transitions', 'Process Centroids'])
        self.sim_type.SetSelection(0)
        setup_simulation = wx.Button(parent=self, label = "Auto Setup Simulation")
        setup_simulation.Bind(event=wx.EVT_BUTTON, handler=self.onAutoSetupSim)
        main_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        main_hsizer.AddSpacer(10)
        main_hsizer.Add(self.sim_type)
        main_hsizer.AddSpacer(145)
        main_hsizer.Add(setup_simulation)
        main_sizer.Add(main_hsizer)
        # Add setup sim button
        main_sizer.AddSpacer(15)
        sim_name_text = wx.StaticText(parent=self, label='Simulation Name')
        self.sim_name = wx.TextCtrl(parent=self, value = '', size=(250,22))
        main_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        main_hsizer.AddSpacer(10)
        main_hsizer.Add(sim_name_text)
        main_hsizer.AddSpacer(10)
        main_hsizer.Add(self.sim_name)
        main_sizer.Add(main_hsizer)
        main_sizer.AddSpacer(10)
        # Add all sections
        main_sizer.Add(network_sizer, 1, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(Inputs_sizer, 1, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(time_sizer, 1, wx.ALL | wx.EXPAND, 10)
        # add run sim button
        run_hsizer = wx.BoxSizer(wx.HORIZONTAL)
        run_hsizer.AddSpacer(10)
        run_simulation = wx.Button(parent=self, label = "Run Simulation")
        run_simulation.Bind(event=wx.EVT_BUTTON, handler=self.onRunSim)
        run_hsizer.Add(run_simulation)     
        run_hsizer.AddSpacer(20)   
        self.running_text = wx.StaticText(self, label='                                            ')
        run_hsizer.Add(self.running_text)      
        run_hsizer.AddSpacer(30)    
        self.Inspect_results = wx.Button(parent=self, label = "View Utilisation Results")
        self.Inspect_results.Bind(event=wx.EVT_BUTTON, handler=self.onInspectResults)
        self.Inspect_results.Disable()
        run_hsizer.Add(self.Inspect_results)
        main_sizer.Add(run_hsizer, wx.ALIGN_BOTTOM)


        OverMain_sizer = wx.BoxSizer(wx.HORIZONTAL)
        OverMain_sizer.Add(main_sizer)
    
        # add the edit sim panel to the right
        self.RightPanel = EditSim(self)
        OverMain_sizer.Add(self.RightPanel, 1, wx.EXPAND | wx.ALL | wx.CENTER)

        self.SetSizer(OverMain_sizer)   


    def onAutoSetupCustom(self):
        """Add edit sim notebook pages - only on first press of auto set up sim."""
        # Add custom panels
        if self.Create_Pages == 0:
            # create pages
            self.RightPanel.tabOne_Pathways =  PathwaysPanel(self.RightPanel.notebook)
            self.RightPanel.tabTwo_Arrivals =  ArrivalsPanel(self.RightPanel.notebook, self)
            self.RightPanel.tabThree_Service = Custom_ServicePanel(self.RightPanel.notebook, self.DataPanel.letters, self.input_service)
            self.RightPanel.tabFour_Capacity =  Custom_CapacityPanel(self.RightPanel.notebook, self, self.SimulationPanel, self.DataPanel.letters)
            self.RightPanel.tabFive_Warmup =  Custom_WarmupPanel(self.RightPanel.notebook, self.DataPanel.dataframe_T4)

            # add pages
            self.RightPanel.notebook.AddPage(self.RightPanel.tabOne_Pathways, "Pathways")
            self.RightPanel.notebook.AddPage(self.RightPanel.tabTwo_Arrivals, "Arrivals")
            self.RightPanel.notebook.AddPage(self.RightPanel.tabThree_Service, "Service")
            self.RightPanel.notebook.AddPage(self.RightPanel.tabFour_Capacity, "Capacity")
            self.RightPanel.notebook.AddPage(self.RightPanel.tabFive_Warmup, "Warm up")
            self.Create_Pages += 1


    def CreateArrivalsGrid(self, ArrivalPeriodGrid, ArrivalsGrid):
        """Fill the arrivals grid depending on simulation data level.
        
        Arrivals can only be edited through automatic re calculation or proportion.
        Set all to read only.
        + Raw Pathways: All arrivals calculated for dummy node
        + Full Transitions: Row per activity arrivals
        + Clustered Transtions: Row per activity arrivals, columns repeated per clusters (k)
        + Process Centroids: Row per centroid
        """
        self.ArrivalPeriodGrid = ArrivalPeriodGrid
        self.ArrivalsGrid = ArrivalsGrid
        
        cols = self.ArrivalsGrid.GetNumberCols()
        rows = self.ArrivalsGrid.GetNumberRows()
        self.ArrivalsGrid.DeleteCols(pos=0, numCols=cols)
        self.ArrivalsGrid.DeleteRows(pos=0, numRows=rows)

        self.ArrivalsGrid.SetDefaultCellBackgroundColour(wx.Colour(240, 240, 240))  

        if self.sim_type_selected == 'Raw Pathways':
            # custom value arrival period
            self.int_choices = wx.grid.GridCellNumberEditor(min=0, max=1000000) 
            self.ArrivalPeriodGrid.SetCellEditor(0,1,self.int_choices)
            # create grid
            self.ArrivalsGrid.AppendCols(4)
            self.ArrivalsGrid.AppendRows(1)
            # change names
            self.ArrivalsGrid.SetColLabelValue(0, 'Individuals')
            self.ArrivalsGrid.SetColLabelValue(1, 'Arrivals per day')
            self.ArrivalsGrid.SetColLabelValue(2, 'Custom Individuals')
            self.ArrivalsGrid.SetColLabelValue(3, 'Custom Arrivals per day')
            for c in range(4):
                self.ArrivalsGrid.SetColSize(c, 155) 
            self.ArrivalsGrid.SetRowLabelValue(0, 'Dummy Node')
            # fill grid
            self.ArrivalsGrid.SetCellValue(0,0,str(len(self.DataPanel.data)))
            self.ArrivalsGrid.SetCellValue(0,1,str(self.input_arrival))

        if self.sim_type_selected == 'Full Transitions':
            Arrival = [self.input_arrival[A]/self.overall_period if self.input_arrival[A] != 0 else 0 for A in range(len(self.DataPanel.letters))]
            # custom value arrival period
            self.int_choices = wx.grid.GridCellNumberEditor(min=0, max=1000000) 
            self.ArrivalPeriodGrid.SetCellEditor(0,1,self.int_choices)
            # create grid
            self.ArrivalsGrid.AppendCols(4)
            self.ArrivalsGrid.AppendRows(len(self.DataPanel.letters))
            # change names
            self.ArrivalsGrid.SetColLabelValue(0, 'Individuals')
            self.ArrivalsGrid.SetColLabelValue(1, 'Arrivals per day')
            self.ArrivalsGrid.SetColLabelValue(2, 'Custom Individuals')
            self.ArrivalsGrid.SetColLabelValue(3, 'Custom Arrivals per day')
            for c in range(4):
                self.ArrivalsGrid.SetColSize(c, 155) 
            # fill grid
            for r, letter in enumerate(self.DataPanel.letters):
                self.ArrivalsGrid.SetRowLabelValue(r, str(letter))
                self.ArrivalsGrid.SetCellValue(r,0,str(self.input_arrival[r]))
                self.ArrivalsGrid.SetCellValue(r,1,str(Arrival[r]))

        if self.sim_type_selected == 'Clustered Transitions':
            # custom value arrival period
            self.int_choices = wx.grid.GridCellNumberEditor(min=0, max=1000000) 
            self.ArrivalPeriodGrid.SetCellEditor(0,1,self.int_choices)
            # create grid
            self.ArrivalsGrid.AppendCols(5*len(self.input_arrival))
            self.ArrivalsGrid.AppendRows(len(self.DataPanel.letters))
            # change names
            for c in range(0, 5*len(self.input_arrival), 5):
                self.ArrivalsGrid.SetColLabelValue(c+1, 'Individuals')
                self.ArrivalsGrid.SetColLabelValue(c+2, 'Arrivals per day')
                self.ArrivalsGrid.SetColLabelValue(c+3, 'Custom Individuals')
                self.ArrivalsGrid.SetColLabelValue(c+4, 'Custom Arrivals per day')
            for r, letter in enumerate(self.DataPanel.letters):
                self.ArrivalsGrid.SetRowLabelValue(r, str(letter))
            # formt grid
            class_no = 0
            for c in range(5*len(self.input_arrival)):
                if c % 5 == 0:
                    self.ArrivalsGrid.SetColSize(c, 10) 
                    self.ArrivalsGrid.SetColLabelValue(c, 'Class ' + str(class_no))
                    for r in range(len(self.DataPanel.letters)):
                        self.ArrivalsGrid.SetCellBackgroundColour(r,c,wx.Colour(250, 135, 72))
                    class_no += 1
                else:
                    self.ArrivalsGrid.SetColSize(c, 155) 
            for cluster in range(len(self.input_arrival)):
                c_input_arrivals = self.input_arrival['Class ' + str(cluster)]
                Arrival = [c_input_arrivals[A]/self.overall_period if c_input_arrivals[A] != 0 else 0 for A in range(len(self.DataPanel.letters))]
                # fill grid
                for r, letter in enumerate(self.DataPanel.letters):
                    self.ArrivalsGrid.SetCellValue(r,(cluster*5)+1,str(c_input_arrivals[r]))
                    self.ArrivalsGrid.SetCellValue(r,(cluster*5)+2,str(Arrival[r]))
        
        if self.sim_type_selected == 'Process Centroids':
            # custom value arrival period
            self.int_choices = wx.grid.GridCellNumberEditor(min=0, max=1000000) 
            self.ArrivalPeriodGrid.SetCellEditor(0,1,self.int_choices)
            # create grid
            self.ArrivalsGrid.AppendCols(5)
            self.ArrivalsGrid.AppendRows(len(self.MainClusteringPanel.process_clustering_results))
            # change names
            self.ArrivalsGrid.SetColLabelValue(0, 'Node Code')
            self.ArrivalsGrid.SetColLabelValue(1, 'Individuals')
            self.ArrivalsGrid.SetColLabelValue(2, 'Arrivals per day')
            self.ArrivalsGrid.SetColLabelValue(3, 'Custom Individuals')
            self.ArrivalsGrid.SetColLabelValue(4, 'Custom Arrivals per day')
            for c in range(5):
                self.ArrivalsGrid.SetColSize(c, 155) 
            # fill grid
            for r, route in enumerate(self.MainClusteringPanel.process_clustering_results[str(self.MainClusteringPanel.process_k)]):
                self.ArrivalsGrid.SetCellValue(r,0,str(route[0]))
            for r, count in enumerate(self.MainClusteringPanel.process_clustering_results['prop_counter_' + str(self.MainClusteringPanel.process_k)]):
                self.ArrivalsGrid.SetCellValue(r,1,str(count))
                self.ArrivalsGrid.SetCellValue(r,2,str(count/self.overall_period))

        # set to read only
        attr = gridlib.GridCellAttr()
        attr.SetReadOnly(True)
        for col in range(self.ArrivalsGrid.GetNumberCols()):
            self.ArrivalsGrid.SetColAttr(col, attr.Clone())


    def CreatePathwaysGrid(self, PathwaysGrid):
        """Fill the Pathways grid depending on simulation data level.
        
        Pathways can NOT be edited and are displayed read only.
        + Raw Pathways: All Pathways performed, with node representation for ciw
        + Full Transitions: Transition matrix between activities
        + Clustered Transtions: Transition matrix between activities, per clusters (k)
        + Process Centroids: Centroids only, with representation value and node representation for ciw
        """
        self.PathwaysGrid = PathwaysGrid
        
        cols = self.PathwaysGrid.GetNumberCols()
        rows = self.PathwaysGrid.GetNumberRows()
        self.PathwaysGrid.DeleteCols(pos=0, numCols=cols)
        self.PathwaysGrid.DeleteRows(pos=0, numRows=rows)

        self.PathwaysGrid.SetDefaultCellBackgroundColour(wx.Colour(240, 240, 240))  
        if self.sim_type_selected == 'Raw Pathways':
            # create grid
            self.PathwaysGrid.AppendCols(2)
            self.PathwaysGrid.AppendRows(len(self.DataPanel.data))
            # change names
            self.PathwaysGrid.SetColLabelValue(0, 'Pathways')
            self.PathwaysGrid.SetColLabelValue(1, 'Routes')
            # fill grid
            for i, pathway in enumerate(self.DataPanel.data.pathways):
                self.PathwaysGrid.SetCellValue(i,0,str(pathway))
            for i, route in enumerate(self.input_routes):
                self.PathwaysGrid.SetCellValue(i,1,str(route))
            self.PathwaysGrid.AutoSizeColumns(setAsMin=True)

        if self.sim_type_selected == 'Full Transitions':
            # create grid
            self.PathwaysGrid.AppendCols(len(self.DataPanel.letters))
            self.PathwaysGrid.AppendRows(len(self.DataPanel.letters))
            # change names
            for index, key in enumerate(self.DataPanel.letters):
                self.PathwaysGrid.SetRowLabelValue(index, key)
                self.PathwaysGrid.SetColLabelValue(index, key)
            # fill grid
            for r, route_row in enumerate(self.input_routes):
                for c in range(len(self.input_routes[0])):
                    if route_row[c] != 0:
                        self.PathwaysGrid.SetCellValue(r,c,str(round(route_row[c],2)))
            self.PathwaysGrid.AutoSizeColumns(setAsMin=True)
        
        if self.sim_type_selected == 'Clustered Transitions':
            # create grid
            self.PathwaysGrid.AppendCols(len(self.input_routes)*(len(self.DataPanel.letters)+1))
            self.PathwaysGrid.AppendRows(len(self.DataPanel.letters))
            # change names
            for index, key in enumerate(self.DataPanel.letters):
                self.PathwaysGrid.SetRowLabelValue(index, key)
            class_no = 0
            for col in range(0, self.PathwaysGrid.GetNumberCols(), len(self.DataPanel.letters)+1):
                self.PathwaysGrid.SetColLabelValue(col, 'Class ' + str(class_no))
                for l, letter in enumerate(self.DataPanel.letters):
                    self.PathwaysGrid.SetCellBackgroundColour(l,col,wx.Colour(250, 135, 72))
                    self.PathwaysGrid.SetColLabelValue(col + 1 + l, letter)
                # fill grid
                c_route = self.input_routes['Class ' + str(class_no)]
                for r, route_row in enumerate(c_route):
                    for c in range(len(c_route[0])):
                        if route_row[c] != 0:
                            self.PathwaysGrid.SetCellValue(r,col + 1 + c,str(round(route_row[c],2)))
                class_no += 1
            self.PathwaysGrid.AutoSizeColumns(setAsMin=True)
            
        if self.sim_type_selected == 'Process Centroids':
            # create grid
            self.PathwaysGrid.AppendCols(2)
            self.PathwaysGrid.AppendRows(len(self.MainClusteringPanel.process_clustering_results))
            # change names
            self.PathwaysGrid.SetColLabelValue(0, 'Centroid Pathway')
            self.PathwaysGrid.SetColLabelValue(1, 'Routes')
            # fill grid
            for i, pathway in enumerate(self.MainClusteringPanel.process_clustering_results[str(self.MainClusteringPanel.process_k)]):
                self.PathwaysGrid.SetCellValue(i,0,str(pathway))
            for i, route in enumerate(self.input_routes):
                self.PathwaysGrid.SetCellValue(i,1,str(route))
            self.PathwaysGrid.AutoSizeColumns(setAsMin=True)

        # set to read only
        attr = gridlib.GridCellAttr()
        attr.SetReadOnly(True)
        for row in range(len(self.DataPanel.data)):
            self.PathwaysGrid.SetRowAttr(row, attr.Clone())


    def onAutoSetupSim(self,event):
        """Get initial simulation variables automated from data - depending on data level selected."""
        self.overall_period = Functions.get_period(self.DataPanel.data, self.DataPanel.headers)
        self.original_individuals = len(self.DataPanel.data)

        name_initial = ['R_', 'F_', 'C_', 'ce_']
        auto_name = name_initial[self.sim_type.GetCurrentSelection()] + 'Basic'
        self.sim_name.SetValue(auto_name)

        self.sim_type_selected = self.sim_type.GetString(self.sim_type.GetCurrentSelection())

        if self.sim_type.GetCurrentSelection() == 0:
            self.current_letters = ['Dummy'] + self.DataPanel.letters
        else:
            self.current_letters = self.DataPanel.letters
            self.draw_network_button.Enable()   

        self.input_arrival, self.input_service, self.input_servers_capacity, self.input_routes, self.draw_matrix  = Functions.AutoSetupInputs(self.sim_type_selected, 
                                                                                                        self.DataPanel.data, 
                                                                                                        self.DataPanel.activity_codes,
                                                                                                        self.DataPanel.multi_activity_codes,
                                                                                                        self.DataPanel.headers, 
                                                                                                        self.current_letters,
                                                                                                        self.original_individuals,
                                                                                                        self.overall_period,
                                                                                                        self.MainClusteringPanel.clustering_results,
                                                                                                        self.MainClusteringPanel.process_k,
                                                                                                        self.MainClusteringPanel.process_clustering_results,
                                                                                                        self.DataPanel.original_name,
                                                                                                        self.MainClusteringPanel.adjust)
        # Setup custom notebook
        self.onAutoSetupCustom()
        self.CreatePathwaysGrid(self.RightPanel.tabOne_Pathways.PathwaysGrid)
        self.CreateArrivalsGrid(self.RightPanel.tabTwo_Arrivals.ArrivalPeriodGrid, self.RightPanel.tabTwo_Arrivals.ArrivalsGrid)
                      
        Info_message = wx.MessageBox(parent=None, message = 'Auto setup simulation complete.', caption='Information',style= wx.OK)


    def onDraw(self, event):
        """Draw network - select view option - opens in pdf.
        
        Not avaliable for Raw Pathways.
        """
        self.current_sim_name = self.sim_name.GetValue()
        draw_file_name = 'Network_' + self.current_sim_name
        Functions.get_draw_network(self.sim_type_selected, self.current_letters, self.draw_matrix, self.DataPanel.SaveLoc, draw_file_name, 
                                    self.MainClusteringPanel.process_k, self.MainClusteringPanel.process_clustering_results, self.MainClusteringPanel.adjust,
                                    LR=False, penwidth=False, round_to=3)
        
        if self.sim_type_selected == 'Clustered Transitions':
            for c_class in self.input_arrival.keys():
                multip_draw_names = draw_file_name + '_' + c_class
                self.plot_options.append(multip_draw_names)
                self.plot_selection.Clear()
                self.plot_selection.AppendItems(self.plot_options)
        elif self.sim_type_selected == 'Process Centroids':
            process_draw_names = [draw_file_name + '_' + str(self.MainClusteringPanel.process_k), 
                                  draw_file_name + '_' + str(self.MainClusteringPanel.process_k) + '_pathways', 
                                  draw_file_name + '_' + str(self.MainClusteringPanel.process_k) + '_linked']
            for name in process_draw_names:
                self.plot_options.append(name)
            self.plot_options.append(draw_file_name + '_' + str(self.MainClusteringPanel.process_k) + '_adjust_' + str(self.MainClusteringPanel.adjust))
            self.plot_selection.Clear()
            self.plot_selection.AppendItems(self.plot_options)
        else:
            self.plot_options.append(draw_file_name)
            self.plot_selection.Clear()
            self.plot_selection.AppendItems(self.plot_options)
        Info_message = wx.MessageBox(parent=None, message = 'Draw complete.', caption='Information',style= wx.OK)


    def getInputs(self):
        """Get simulation input variables depending on auto or custom selection.
        
        + Variables: Arrivals, Service, Capacirty/Servers, Warm up
        + Number of individuals taken from Arrivals top row
        """
        # Get arrivals
        arrivalgrid_columns = [self.RightPanel.tabTwo_Arrivals.ArrivalsGrid.GetColLabelValue(c) for c in range(self.ArrivalsGrid.GetNumberCols())]
        self.arrivals = []
        for c, column in enumerate(arrivalgrid_columns):
            if self.arrivals_choice.GetCurrentSelection() == 1: 
                if column == 'Custom Arrivals per day':
                    get_arrivals = [float(self.RightPanel.tabTwo_Arrivals.ArrivalsGrid.GetCellValue(r, c)) if self.RightPanel.tabTwo_Arrivals.ArrivalsGrid.GetCellValue(r, c) != '' else 0 
                                    for r in range(self.RightPanel.tabTwo_Arrivals.ArrivalsGrid.GetNumberRows())]
                    self.arrivals.append(get_arrivals)
            else:
                if column == 'Arrivals per day':
                    get_arrivals = [float(self.RightPanel.tabTwo_Arrivals.ArrivalsGrid.GetCellValue(r, c)) if self.RightPanel.tabTwo_Arrivals.ArrivalsGrid.GetCellValue(r, c) != '' else 0 
                                    for r in range(self.RightPanel.tabTwo_Arrivals.ArrivalsGrid.GetNumberRows())]
                    self.arrivals.append(get_arrivals)

        # Get service
        if self.service_choice.GetCurrentSelection() == 1:
            self.service = {code: [self.RightPanel.tabThree_Service.ServiceGrid.GetCellValue(r,2),
                                   float(self.RightPanel.tabThree_Service.ServiceGrid.GetCellValue(r,3))] if self.RightPanel.tabThree_Service.ServiceGrid.GetCellValue(r,2) != '' or 
                                   self.RightPanel.tabThree_Service.ServiceGrid.GetCellValue(r,3) != '' else ['Determinisic', 0.1] for r, code in enumerate(self.DataPanel.letters)}
        else:
            self.service = {code: [self.RightPanel.tabThree_Service.ServiceGrid.GetCellValue(r,0),
                                   float(self.RightPanel.tabThree_Service.ServiceGrid.GetCellValue(r,1))] for r, code in enumerate(self.DataPanel.letters)}

        # Get capacity
        days = int(self.time_unit_item.GetString(self.time_unit_item.GetCurrentSelection())[0])
        # pattern
        if self.capacity_choice.GetCurrentSelection() == 1:
            self.capacity = {code: [int(self.RightPanel.tabFour_Capacity.BottomCapGrid.GetCellValue(r,c)) if self.RightPanel.tabFour_Capacity.BottomCapGrid.GetCellValue(r,c) != '' else 0 
                                    for c in range(days)] for r, code in enumerate(self.DataPanel.letters)}
        else:
            self.capacity = {code: cap[:days] for code, cap in self.input_servers_capacity.items()}
        
        # Get Warmup
        # warm start
        if self.warmup_type.GetCurrentSelection() == 1:
            if self.warm_choice.GetCurrentSelection() == 1:
                self.warm = [int(self.RightPanel.tabFive_Warmup.WarmupGrid.GetCellValue(r+2,1)) if self.RightPanel.tabFive_Warmup.WarmupGrid.GetCellValue(r+2,1) != '' else 0 for r, code in enumerate(self.DataPanel.letters)]
            else:
                self.warm = [int(self.RightPanel.tabFive_Warmup.WarmupGrid.GetCellValue(r+2,0)) if self.RightPanel.tabFive_Warmup.WarmupGrid.GetCellValue(r+2,0) != '' else 0  for r, code in enumerate(self.DataPanel.letters)]
        # warm itterative
        elif self.warmup_type.GetCurrentSelection() == 2:
            if self.warm_choice.GetCurrentSelection() == 1:
                if self.RightPanel.tabFive_Warmup.WarmupGrid.GetCellValue(0,1) == '':
                    self.warm = 1
                else:
                    self.warm = int(self.RightPanel.tabFive_Warmup.WarmupGrid.GetCellValue(0,1))
            else:
                self.warm = int(self.RightPanel.tabFive_Warmup.WarmupGrid.GetCellValue(0,0))
        else:
            self.warm = [0 for code in self.DataPanel.letters]

        # Get no. individuals to run
        if self.inds_choice.GetCurrentSelection() == 1:
            self.individuals = int(self.RightPanel.tabTwo_Arrivals.ArrivalPeriodGrid.GetCellValue(0, 1))
            if self.sim_type_selected == 'Raw Pathways':
                if self.individuals > self.original_individuals:
                    self.individuals = self.original_individuals
        else:
            self.individuals = int(self.RightPanel.tabTwo_Arrivals.ArrivalPeriodGrid.GetCellValue(0, 0))


    def onRunSim(self, event):
        """Runs simulation - Basic or trials - produces results tables and plots."""
        # Get simulation inputs
        self.getInputs()
        # get trials
        self.trials = self.time_trials.GetValue()

        # Get number of clusters
        if self.sim_type_selected == 'Clustered Transitions':
            cluster_k = len(self.arrivals)
        elif self.sim_type_selected == 'Process Centroids':
            cluster_k = len(self.arrivals[0])
        else:
            cluster_k = 0

        # percentage with x days target
        self.DataPanel.target = int(self.target_choice.GetValue())

        # ensure sim name is unique
        if self.sim_name.IsModified() == False:
            self.all_sim_names = []
        if self.sim_name.GetValue() in self.all_sim_names:
            error_message = wx.MessageBox(parent=None, message = 'Please enter a unique simulation name in the \'Simulation Name\' box. \n Already used: ' + ', '.join(self.all_sim_names), 
                                        caption='Error',style= wx.OK)
        else:
            self.week_type = self.time_unit_item.GetString(self.time_unit_item.GetCurrentSelection())
            self.warm_type = self.warmup_type.GetString(self.warmup_type.GetCurrentSelection())

            self.running_text.SetLabel('Please wait...')
            self.current_sim_name = self.sim_name.GetValue()
            # Add trials and runs to sim name if trials selected
            if self.trials != 1:
                self.current_sim_name = self.current_sim_name + '_Trials_' + str(self.trials)
        
            # Construct simulation network
            self.Network, self.Servers_Schedules, self.time_run, self.individuals = Functions.ConstructSim(self.sim_type_selected, self.week_type, self.warm_type, self.DataPanel.letters, self.individuals, self.overall_period, cluster_k,
                                                                    self.arrivals, self.service, self.capacity, self.warm, self.input_routes)

            # Run basic if trials = 1
            if self.trials == 1:
                self.sim_seed = self.sim_seed_item.GetValue()
                self.Q = Functions.RunBasicSim(self.Network, self.sim_seed, self.time_run)

                self.DataPanel.dataframe_T1, self.DataPanel.dataframe_T2, self.DataPanel.dataframe_T3, self.DataPanel.dataframe_T4, self.df_utilisation = Functions.RunSimData(self.Q, self.warm_type, self.warm, self.current_letters, self.Servers_Schedules, self.week_type,
                                                                                                                                                            self.DataPanel.dataframe_T1, self.DataPanel.dataframe_T2, 
                                                                                                                                                            self.DataPanel.dataframe_T3, self.DataPanel.dataframe_T4, 
                                                                                                                                                            self.DataPanel.original_transitions, 
                                                                                                                                                        self.DataPanel.activity_codes, self.DataPanel.target, self.time_run, 
                                                                                                                                                        self.DataPanel.SaveLoc, simulation_name=self.current_sim_name, basic=True)
                # enable view utilisation
                self.Inspect_results.Enable()
            # Run trials if trials > 1
            else:
                self.DataPanel.dataframe_T1, self.DataPanel.dataframe_T2, self.DataPanel.dataframe_T4 = Functions.RunTrialSim(self.Network, self.trials, self.time_run, self.warm_type, self.warm, self.current_letters, self.Servers_Schedules, self.week_type,
                                                                                                                                                            self.DataPanel.dataframe_T1, self.DataPanel.dataframe_T2, 
                                                                                                                                                            self.DataPanel.dataframe_T3, self.DataPanel.dataframe_T4, 
                                                                                                                                                            self.DataPanel.original_transitions, 
                                                                                                                                                        self.DataPanel.activity_codes, self.DataPanel.target, self.time_run, 
                                                                                                                                                        self.DataPanel.SaveLoc, simulation_name=self.current_sim_name, basic=False)
                # disable view utilisation
                self.Inspect_results.Disable()

            # Gather all simulation inputs
            self.Arrivals_Dict[self.current_sim_name] = self.arrivals
            self.Service_Dict[self.current_sim_name] = self.service
            self.Capacity_Dict[self.current_sim_name] = self.capacity
            self.Routing_Dict[self.current_sim_name] = self.input_routes
            
            self.running_text.SetLabel('                                            ')
            self.sim_name.SetModified(True)
            self.all_sim_names.append(self.current_sim_name)

            Info_message = wx.MessageBox(parent=None, message = '\'' + self.current_sim_name + '\' simulation complete.', caption='Information',style= wx.OK)       


    def onViewNetwork(self, event):
        """View pdf of selected network"""
        plot = self.plot_selection.GetString(self.plot_selection.GetCurrentSelection())
        Netork_location = self.DataPanel.SaveLoc + 'Network_diagrams/' + plot + '.pdf'
        os.startfile(Netork_location)


    def onInspectResults(self, event):
        """View utilisation results"""
        UtilResultsGrid(self.DataPanel, self.SimulationPanel).Show()


#-------------- Capacity Panels ---------------
class CapacityInputGrid(wx.Panel):
    """Capacity panel for capacity calaculation user selection inputs."""
    def __init__(self, parent, DataPanel, ModelSimPanel, SimulationPanel, BottomResultsPanel):
        wx.Panel.__init__(self, parent=parent)
        """Initialise empty input grid."""
        self.DataPanel = DataPanel  
        self.ModelSimPanel = ModelSimPanel
        self.SimulationPanel = SimulationPanel
        self.BottomResultsPanel = BottomResultsPanel

        self.num_calculations = 0
        self.num_setup = 0
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddSpacer(10)

        # top buttons
        capacity_sizer = wx.BoxSizer(wx.HORIZONTAL)
        capacity_sizer.AddSpacer(5)
        AutoSetup_capacity = wx.Button(parent=self, label = "Set up Capacity")
        AutoSetup_capacity.Bind(event=wx.EVT_BUTTON, handler=self.onAutoSetupCapacity)
        capacity_sizer.Add(AutoSetup_capacity)
        capacity_sizer.AddSpacer(10)
        calc_capacity = wx.Button(self, label='Calculate')
        calc_capacity.Bind(event=wx.EVT_BUTTON, handler=self.onCalcCapacity)
        capacity_sizer.Add(calc_capacity)
        capacity_sizer.AddSpacer(10)
        self.running_text = wx.StaticText(self, label='                                                                                        ')
        self.running_text.SetBackgroundColour(wx.Colour(240, 240, 240))
        capacity_sizer.Add(self.running_text)   
        
        # grid
        self.InputGrid = gridlib.Grid(self)
        self.InputGrid.CreateGrid(0,6)
        self.InputGrid.SetColLabelValue(0, 'Target (%)')
        self.InputGrid.SetColLabelValue(1, 'Target Time (days)')
        self.InputGrid.SetColLabelValue(2, 'No. of Increments')
        self.InputGrid.SetColLabelValue(3, 'Increment Amount')
        self.InputGrid.SetColLabelValue(4, 'Plot Max (days)')
        self.InputGrid.SetColLabelValue(5, 'Run')
        for c in range(6):
            self.InputGrid.SetColSize(c, 115)


        sizer.Add(capacity_sizer)
        sizer.Add(self.InputGrid, 1, wx.EXPAND | wx.ALL)

        self.SetSizer(sizer)


    def onAutoSetupCapacity(self, event):
        """Fill capacity input grid with default options."""
        # Initial empty dictionary to collect results
        if len(self.SimulationPanel.CalculatedCapacity) == 1:
            self.SimulationPanel.CalculatedCapacity['Initial'] = {activity: '' for activity in self.DataPanel.letters}
            self.calc_name = 'Initial'
        
        # Setup Input grid
        if self.num_setup == 0:
            self.InputGrid.AppendRows(len(self.DataPanel.letters))
        # default target days from overall target / num of activities
        target_days = int(int(self.ModelSimPanel.target_choice.GetValue()) / len(self.DataPanel.letters))
        # minimum 1
        if target_days == 0:
            target_days = 1
        # default inputs
        initial_capacity_inputs = [90,target_days,5,5,25,'Yes']
        for i, cap_input in enumerate(initial_capacity_inputs):   
            for index, key in enumerate(self.DataPanel.letters):
                self.InputGrid.SetCellValue(index,i,str(cap_input))

        self.int_choices = wx.grid.GridCellNumberEditor(min=0, max=1000000) 
        for index, key in enumerate(self.DataPanel.letters):
            for c in range(5):
                self.InputGrid.SetCellEditor(index,c,self.int_choices)

        self.run_choices = wx.grid.GridCellChoiceEditor(['Yes', 'No'], False)
        for index, key in enumerate(self.DataPanel.letters):
            self.InputGrid.SetRowLabelValue(index, key)
            if self.num_setup == 0:
                self.InputGrid.SetCellEditor(index, 5, self.run_choices)        

        # prepare results grid
        if self.num_setup == 0:
            self.BottomResultsPanel.ResultsGrid.AppendRows(len(self.DataPanel.letters))
            for index, key in enumerate(self.DataPanel.letters):
                self.BottomResultsPanel.ResultsGrid.SetRowLabelValue(index, key)
        
        self.num_setup += 1


    def onCalcCapacity(self, event):
        """Calculate steady state capacity and retrun capacity slots a week per activity."""
        self.running_text.SetLabel('Calculating: Please wait...')
        # get 5 or 7 days
        days_a_week = self.ModelSimPanel.time_unit_item.GetCurrentSelection()
        cap_input_dict = {}
        for a, activity in enumerate(self.DataPanel.letters):
            row_values = [self.InputGrid.GetCellValue(a, c) for c in range(6)]
            cap_input_dict[activity] = row_values
        # perform calculation
        self.calc_name, current_CalculatedCapacity, current_pattern = Functions.CalculateCapacity(self.DataPanel.SaveLoc, self.num_calculations, 
                                                                              self.DataPanel.data, self.DataPanel.activity_codes, self.SimulationPanel.CalculatedCapacity[self.calc_name],
                                                                              cap_input_dict, self.DataPanel.initial_overall_period, days_a_week, self.DataPanel.original_name)
        self.SimulationPanel.CalculatedCapacity[self.calc_name] = current_CalculatedCapacity
        self.SimulationPanel.CalculatedPattern[self.calc_name] = current_pattern
        self.running_text.SetLabel('                                                                                        ')

        # fill results grid
        self.BottomResultsPanel.ResultsGrid.AppendCols(1)
        self.BottomResultsPanel.ResultsGrid.SetColLabelValue(self.num_calculations, self.calc_name)
        for index, key in enumerate(self.DataPanel.letters):
            self.BottomResultsPanel.ResultsGrid.SetCellValue(index,self.num_calculations,str(self.SimulationPanel.CalculatedCapacity[self.calc_name][key][2]))
            if self.SimulationPanel.CalculatedCapacity[self.calc_name][key][3] == 'Yes':
                self.BottomResultsPanel.ResultsGrid.SetCellTextColour(index,self.num_calculations, wx.Colour(201, 56, 8))
        self.BottomResultsPanel.ResultsGrid.AutoSizeColumns(setAsMin=True)
        
        # set to read only
        attr = gridlib.GridCellAttr()
        attr.SetReadOnly(True)
        for col in range(self.BottomResultsPanel.ResultsGrid.GetNumberCols()):
            self.BottomResultsPanel.ResultsGrid.SetColAttr(col, attr.Clone())

        self.num_calculations += 1


class CapacityPanel(wx.Panel):
    """Main Capacity panel for capacity calculation."""
    def __init__(self, parent, DataPanel, ModelSimPanel, SimulationPanel):
        wx.Panel.__init__(self, parent)
        """Set up main capacity panel.
        
        Panel split:
        + Top: Capacity input grid
        + Bottom: Results grid
        + Right: canvas panel for plot        
        """
        self.DataPanel = DataPanel
        self.ModelSimPanel = ModelSimPanel
        self.SimulationPanel = SimulationPanel

        mainSplitter = wx.SplitterWindow(self)
        LeftSplitter = wx.SplitterWindow(mainSplitter)

        self.BottomPanel = ResultsGridPanel(LeftSplitter)
        table_name = wx.StaticText(self.BottomPanel, label='Results: Slots per week.')
        self.TopPanel = CapacityInputGrid(LeftSplitter, DataPanel, ModelSimPanel, SimulationPanel,self.BottomPanel)
        LeftSplitter.SplitHorizontally(self.TopPanel, self.BottomPanel)
        LeftSplitter.SetSashGravity(0.5)
        self.RightPanel = CanvasFrame(mainSplitter, DataPanel, canvasPanel=self.SimulationPanel, plotParent="Capacity")
        mainSplitter.SplitVertically(LeftSplitter, self.RightPanel)
        mainSplitter.SetSashGravity(0.5)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(mainSplitter, 1, wx.EXPAND)
        self.SetSizer(main_sizer) 


#----------------- Results -------------------
class SimResultsTables(wx.Panel):
    """Simulation main results tables panel."""
    def __init__(self, parent, DataPanel):
        """Set up panel for four main results tables.
        
        Split panel
        + Top: T1 - main highligh simualtion results
        + Bottom Left: T2 - Actvity frequency
        + Bottom Middle: T3 - Frequency of top 10 occuring pathways
        + Bottom Right: T4 - Activity waiting times        
        """
        wx.Panel.__init__(self, parent)
        topSplitter = wx.SplitterWindow(self)
        hSplitter = wx.SplitterWindow(topSplitter)
        self.DataPanel = DataPanel
               
        
        self.BL_T2 = ResultsGridPanel(hSplitter)
        table_name = wx.StaticText(self.BL_T2, label='Table 2: Activity Frequency')
        self.BM_T3 = ResultsGridPanel(hSplitter)
        table_name = wx.StaticText(self.BM_T3, label='Table 3: Frequency of top 10 occuring pathways')
        hSplitter.SplitVertically(self.BL_T2, self.BM_T3)
        hSplitter.SetSashGravity(0.5)
        self.BR_T4 = ResultsGridPanel(topSplitter)
        table_name = wx.StaticText(self.BR_T4, label='Table 4: Activity Wait times (days)')
        topSplitter.SplitVertically(hSplitter, self.BR_T4)
        topSplitter.SetSashGravity(0.66)
        
        self.T_T1 = ResultsGridPanel(self)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        update_button = wx.Button(self, label='Update')
        update_button.Bind(event=wx.EVT_BUTTON, handler=self.onUpdateResults)
        sizer.Add(update_button)
        table_name = wx.StaticText(self.T_T1, label='Table 1: Simulation summary results')
        sizer.Add(self.T_T1, 1, wx.EXPAND)
        sizer.Add(topSplitter, 1, wx.EXPAND)
        self.SetSizer(sizer)


    def onUpdateResults(self, event):
        """Update results by adding any results run but not currently on grid."""
        dataframes = [self.DataPanel.dataframe_T1, self.DataPanel.dataframe_T2, self.DataPanel.dataframe_T3, self.DataPanel.dataframe_T4]
        tables_panels = [self.T_T1, self.BL_T2, self.BM_T3, self.BR_T4]

        dimensions = [self.DataPanel.dataframe_T1.shape, self.DataPanel.dataframe_T2.shape, self.DataPanel.dataframe_T3.shape, self.DataPanel.dataframe_T4.shape]
        grid_dimensions =  [(table.ResultsGrid.GetNumberRows(), table.ResultsGrid.GetNumberCols()) for table in tables_panels]
        
        if grid_dimensions != dimensions:
            for T, results_df in enumerate(dataframes):
                row_difference = dimensions[T][0] - grid_dimensions[T][0]
                col_difference = dimensions[T][1] - grid_dimensions[T][1]
                # add rows & columns
                tables_panels[T].ResultsGrid.AppendCols(numCols = col_difference)
                tables_panels[T].ResultsGrid.AppendRows(numRows = row_difference)
                # fill
                for c in range(col_difference):
                    col_pos = grid_dimensions[T][1]+c
                    for r in range(dimensions[T][0]):
                        tables_panels[T].ResultsGrid.SetCellValue(r,col_pos,str(results_df.iloc[r][col_pos]))
                for r in range(row_difference):
                    row_pos = grid_dimensions[T][0]+r
                    for c in range(dimensions[T][1]):
                        tables_panels[T].ResultsGrid.SetCellValue(row_pos,c,str(results_df.iloc[row_pos][c]))
                # update column names 
                for i, col in enumerate(results_df.columns):
                    tables_panels[T].ResultsGrid.SetColLabelValue(i, col)
                tables_panels[T].ResultsGrid.AutoSizeColumns()

                attr = gridlib.GridCellAttr()
                attr.SetReadOnly(True)
                for row in range(tables_panels[T].ResultsGrid.GetNumberRows()):
                    tables_panels[T].ResultsGrid.SetRowAttr(row, attr.Clone())

   
#-------------- Sim Main Panel ---------------
class SimulationPanel(wx.Panel):
    """Main Simulation tab panel."""
    def __init__(self, parent, DataPanel, MainClusteringPanel):
        wx.Panel.__init__(self, parent)
        """Set up simulation notebook for model, capacity and results panels."""
        self.SetBackgroundColour(wx.Colour(240, 240, 240))
        
        self.CalculatedCapacity = {'Initial' : {}}
        self.CalculatedPattern = {'Initial' : {}}

        # Notebook
        notebook = wx.Notebook(self)
        self.tabOne_Setup = ModelSimPanel(notebook, DataPanel, MainClusteringPanel, self)
        notebook.AddPage(self.tabOne_Setup, "Model")
        tabLast_Capacity = CapacityPanel(notebook, DataPanel, self.tabOne_Setup, self)
        notebook.AddPage(tabLast_Capacity, "Capacity")
        tabThree_TableResults = SimResultsTables(notebook, DataPanel)
        notebook.AddPage(tabThree_TableResults, "Simulation Results")
    
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(notebook, 1, wx.EXPAND)
        self.SetSizer(sizer)


#============== Visulisation  ===============
class plottingPanel(wx.Panel):
    """Plotting panel."""
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        """Set up plot panel - hold Sim.Pro.Flow logo."""
        self.mainsizer = wx.BoxSizer(wx.VERTICAL)

        self.figure = Figure()
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.mainsizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.EXPAND)
        self.SetSizer(self.mainsizer)
        self.Fit()

        self.axes = self.figure.add_subplot(111)
        img = plt.imread("Sim.Pro.Flow_Logo.png")
        self.axes.clear()
        self.axes.imshow(img)   
        self.axes.set_xticks([])
        self.axes.set_yticks([])
        self.axes.axis('equal')
        self.figure.subplots_adjust(bottom=0, top=1, left=0, right=1)

        self.add_toolbar() 


    def add_toolbar(self):
        """Add navigation toolbar"""
        self.toolbar = NavigationToolbar(self.canvas)
        self.toolbar.Realize()
        self.mainsizer.Add(self.toolbar, 0, wx.LEFT | wx.EXPAND)
        self.toolbar.update()
     

class VisPlots(wx.Panel):
    """Visulisation plots panel."""
    def __init__(self, parent, DataPanel, SimulationPanel, plot_type):
        wx.Panel.__init__(self, parent)
        """Set up generic visulisation of plots panel.
        
        + options for update, choices and view.
        Split panel left and right
        + plot_type = Total time - Left: original data, Right: selected simulation
        + plot_type = Wait -  total time in system - Left: original data, Right: selected simulation
        + plot_type = Util - simulation utilisation results -  Left: original data, Right: selected simulation        
        """
        self.DataPanel = DataPanel
        self.SimulationPanel = SimulationPanel
        self.plot_type = plot_type
        topSplitter = wx.SplitterWindow(self)

        self.Left = plottingPanel(topSplitter)
        self.Right = plottingPanel(topSplitter)
        topSplitter.SplitVertically(self.Left, self.Right)
        topSplitter.SetSashGravity(0.5)
        topSplitter.SetMinimumPaneSize(1)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.AddSpacer(10)
        self.hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.hsizer.AddSpacer(10)
        self.update_button = wx.Button(self, label='Update')
        self.update_button.Bind(event=wx.EVT_BUTTON, handler=self.onPlotSelect)
        self.hsizer.Add(self.update_button)
        self.hsizer.AddSpacer(10)
        self.plot_selection = wx.Choice(self, choices=[], size=(200, 25))
        self.hsizer.Add(self.plot_selection)
        self.hsizer.AddSpacer(10)
        self.view_button = wx.Button(self, label='View')
        self.view_button.Bind(event=wx.EVT_BUTTON, handler=self.onView)
        self.hsizer.Add(self.view_button)
        self.hsizer.AddSpacer(10)
        if plot_type == 'TotalTime':
            Title = wx.StaticText(self, label='Total Time in System - Left: Original Data, Right: Selected Simulation')
        if plot_type == 'Wait':
            Title = wx.StaticText(self, label='Waiting time per activity - Left: Original Data, Right: Selected Simulation')
        if plot_type == 'Util':
            Title = wx.StaticText(self, label='Left: Utilisation Percentage of Selected Simulation, Right: Remaining Queue of Selected Simulation')
        self.hsizer.Add(Title)
        self.sizer.Add(self.hsizer)
        
        self.sizer.Add(topSplitter, 1, wx.EXPAND)
        self.SetSizer(self.sizer)
    

    def add_plot(self, panel, plot):    
        """Add image to plot canvas"""
        img = plt.imread(plot)
        panel.axes.clear()
        panel.axes.imshow(img)   
        panel.axes.set_xticks([])
        panel.axes.set_yticks([])
        panel.axes.axis('equal')


    def onPlotSelect(self, event):
        """Select plot to add to plot canvas"""
        self.plot_selection.Clear()
        plot_names = [name for name in self.SimulationPanel.tabOne_Setup.all_sim_names if '_Trials_' not in name]
        self.plot_selection.AppendItems(plot_names)
    

    def onView(self, event):
        """View selected plot - depending on plot_type"""
        sim_name = self.plot_selection.GetString(self.plot_selection.GetCurrentSelection())
        if self.plot_type == 'TotalTime':
            Left_plot = self.DataPanel.SaveLoc + 'Plots/Simulation/TotalTime_' + self.DataPanel.original_name + '.png'
            self.add_plot(self.Left, Left_plot)
            if sim_name != '':
                Right_plot = self.DataPanel.SaveLoc + 'Plots/Simulation/TotalTime_' + sim_name + '.png'
                self.add_plot(self.Right, Right_plot)
        if self.plot_type == 'Wait':
            Left_plot = self.DataPanel.SaveLoc + 'Plots/Simulation/Activity_Waits_' + self.DataPanel.original_name + '.png'
            self.add_plot(self.Left, Left_plot)
            if sim_name != '':
                Right_plot = self.DataPanel.SaveLoc + 'Plots/Simulation/Activity_Waits_' + sim_name + '.png'
                self.add_plot(self.Right, Right_plot)
        if self.plot_type == 'Util':
            Left_plot = self.DataPanel.SaveLoc + 'Plots/Simulation/Utilisation_Percent_' + sim_name + '.png'
            self.add_plot(self.Left, Left_plot)
            if sim_name != '':
                Right_plot = self.DataPanel.SaveLoc + 'Plots/Simulation/Utilisation_Queue_' + sim_name + '.png'
                self.add_plot(self.Right, Right_plot)


#-------------- Vis Main Panel ---------------
class VisulisationPanel(wx.Panel):
    """Main Visulisation tab panel."""
    def __init__(self, parent, DataPanel, SimulationPanel):
        wx.Panel.__init__(self, parent)
        """Set up notebook tabs - total time plots, wait time plots, utilisation plots."""
        self.SetBackgroundColour(wx.Colour(240, 240, 240))
        
        # Notebook
        notebook = wx.Notebook(self)
        self.tabOne_WaitPlots = VisPlots(notebook, DataPanel, SimulationPanel, plot_type='TotalTime')
        notebook.AddPage(self.tabOne_WaitPlots, "Total Time")
        self.tabTwo_ActWaitPlots = VisPlots(notebook, DataPanel, SimulationPanel, plot_type='Wait')
        notebook.AddPage(self.tabTwo_ActWaitPlots, "Waiting Time Plots")
        self.tabThree_UtilPlots = VisPlots(notebook, DataPanel, SimulationPanel, plot_type='Util')
        notebook.AddPage(self.tabThree_UtilPlots, "Utilisation Plots")
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(notebook, 1, wx.ALL|wx.EXPAND, 5)
        self.SetSizer(sizer)


#============== Hold Panel ===============
class HoldPanel(wx.Panel):
    """Panel to be used as placeholder"""
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)
        """Panel with Sim.Pro.Flow logo expanded to panel size."""
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        image = 'Sim.Pro.Flow_Logo.png'
        bmp_image = wx.Image(image, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        bitmap1 = wx.StaticBitmap(self, -1, bmp_image, (0, 0), (10,20))
        sizer.Add(bitmap1, 1, wx.EXPAND | wx.ALL | wx.CENTER)

        self.SetSizer(sizer)
        

class AboutFrame(wx.Frame):
    """About Frame."""
    def __init__(self):
        wx.Frame.__init__(self, parent=None, title='About', pos=(320,320), size=(1015,200))
        """Set up about frame.
        
        + official about box will appear
        + on close about box, funder logos will open in frame
        """
        self.SetBackgroundColour(wx.Colour(240, 240, 240))

        about = wx.adv.AboutDialogInfo()
        about.SetName('Sim.Pro.Flow')
        about.SetVersion('Prototype 2.0')
        about.SetDescription('Sim.Pro.Flow is a decision support tool that allows for mapping, modelling and scenario testing of a system. '+
                                'Sim.Pro.Flow works from pathway strings generated from date stamp data. ' +
                                'The main feature of Sim.Pro.Flow is to automate the build and visulisation of a discrete event simulation. ' +
                                'This prototype was build as part of a learning exercise to contribute to a PhD project, ' +
                                'in collaboration with Velindre Cancer Centre. \n' +
                                '\n' +
                                'Sim.Pro.Flow is in prototype development phase and as such has not gone through extensive user testing or error checking. ' +
                                'By using Sim.Pro.Flow the user takes on all responsibility to ensure that the process and as such all results are correct. \n'+
                                '\n' +
                                'Acknowledgements: Paul Harper, Daniel Gartner, Geraint Palmer, Edilson Arruda. \n' +
                                'Funders: KESS2 and Cancer Research UK')
        about.AddDeveloper('Emma Aspland')
        wx.adv.AboutBox(about)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        logos = 'Funder_Logos.png'
        bmp_image = wx.Image(logos, wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        bitmap = wx.StaticBitmap(self, -1, bmp_image, (0, 0), (10,20))
        sizer.Add(bitmap, 1, wx.EXPAND | wx.ALL | wx.CENTER)
        self.SetSizer(sizer)


#============== Main Frame ===============
class MainFrame(wx.Frame):
    """Main frame."""
    def __init__(self):
        wx.Frame.__init__(self, None, title="Sim.Pro.Flow Prototype")
        """Set up the main frame.
        
        + Menu bar with about, help and export functions
        + data, clustering, simulation and visulisation notebook tabs"""
        panel = wx.Panel(self)
        self.requestQ = Queue.Queue()
        self.resultQ = Queue.Queue()
        
        notebook = wx.Notebook(panel)
        self.data_tab = DataPanel(notebook)
        notebook.AddPage(self.data_tab, "Data")
        Cluster_tab = MainClusteringPanel(notebook, self.data_tab, self.requestQ, self.resultQ)
        notebook.AddPage(Cluster_tab, "Clustering")
        self.sim_tab = SimulationPanel(notebook, self.data_tab, Cluster_tab)
        notebook.AddPage(self.sim_tab, "Simulation")  
        Vis_tab = VisulisationPanel(notebook, self.data_tab, self.sim_tab)
        notebook.AddPage(Vis_tab, "Visulisation")

        TopMenuBar = wx.MenuBar()
        File_Menu = wx.Menu()
        About_File_MenuItem = File_Menu.Append(wx.NewId(), 'About', 'View the about box.')
        self.Bind(wx.EVT_MENU, self.onFileAbout, About_File_MenuItem)
        Help_File_MenuItem = File_Menu.Append(wx.NewId(), 'Help', 'Open the help documents.')
        self.Bind(wx.EVT_MENU, self.onFileHelp, Help_File_MenuItem)
        Export_File_MenuItem = File_Menu.Append(wx.NewId(), 'Export', 'Save the raw python code.')
        self.Bind(wx.EVT_MENU, self.onFileExport, Export_File_MenuItem)
        TopMenuBar.Append(File_Menu, 'File')
        self.SetMenuBar(TopMenuBar)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(notebook, 1, wx.ALL|wx.EXPAND, 5)
        panel.SetSizer(sizer)
        self.Layout()
        
        self.Show()
        self.Maximize(True)
        
        # open about box on load
        AboutFrame().Show()

    def onFileAbout(self, event):
        """Show the about frame"""
        AboutFrame().Show()

    def onFileHelp(self, event):
        """Open pdf help file."""
        os.startfile('SimProFlow_Help.pdf')

    def onFileExport(self, event):
        """Save arrivals, service, capacity and routing dictionaries in .py file for use outside Sim.Pro.Flow."""
        with open(self.data_tab.SaveLoc + 'Raw_Variables.py', 'w') as pydoc:
            pydoc.writelines('Arrivals_Dict' + ' = ' + str(self.sim_tab.tabOne_Setup.Arrivals_Dict))
            pydoc.writelines('\n')
            pydoc.writelines('Service_Dict' + ' = ' + str(self.sim_tab.tabOne_Setup.Service_Dict))
            pydoc.writelines('\n')
            pydoc.writelines('Capacity_Dict' + ' = ' + str(self.sim_tab.tabOne_Setup.Capacity_Dict))
            pydoc.writelines('\n')
            pydoc.writelines('Routing_Dict' + ' = ' + str(self.sim_tab.tabOne_Setup.Routing_Dict))


#----------------------------------------------------------------------
if __name__ == "__main__":
    app = wx.App(False)
    frame = MainFrame()
    app.MainLoop()
