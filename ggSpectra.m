classdef ggSpectra < Modules.Experiment
    
    properties(SetObservable,AbortSet)
        data
        ip = '10.16.0.182';
        grating = '';
        flake  = '';
        emitter='';
        center_wl = 620;       % Grating center_wl
        exposure = 1000;         % Seconds
        cursor_x = 0
        cursor_y = 0
        prefs = {'ip'}; % Not including winspec stuff because it can take a long time!
        show_prefs = {'center_wl','exposure','grating','ip','flake', 'emitter'};
    end
    
    properties(SetAccess=private,Hidden)
        Spectrometer
        listeners
    end
    
    methods(Access=private)
        function obj = ggSpectra()
            %obj.path = 'spectrometer';
            obj.Spectrometer = hwserver(obj.ip);
            obj.center_wl = obj.Spectrometer.com('Spectrometer','get_center_wavelength');
            obj.exposure = obj.Spectrometer.com('Spectrometer','get_exposure_time');
            obj.grating = obj.Spectrometer.com('Spectrometer','get_grating');
            obj.data = [];
            
            try
                obj.loadPrefs; % Load prefs should load WinSpec via set.ip
            catch err % Don't need to raise alert here
                if ~strcmp(err.message,'Spectrometer not set')
                    rethrow(err)
                end
            end
        end
    end
 
    methods(Static)
        function obj = instance()
            mlock;
            persistent Object
            if isempty(Object) || ~isvalid(Object)
                Object = Experiments.ggSpectra();
            end
            obj = Object;
        end
    end
    
    
    methods 
        function run(obj, status, managers, ax)
            % Main run method (callback for CC run button)
            obj.Spectrometer = hwserver(obj.ip);
            status.String = 'Experiment started';
            obj.data = [];
            drawnow;
            
            obj.Spectrometer.com('Spectrometer','move_spe');
            
            
            stage = managers.Imaging.active_module.uses_stage;
            assert(logical(managers.Stages.check_module_str(stage)),'Stage associated with active imager is not loaded.');
            managers.Stages.setActiveModule(stage);
            startingPos = managers.Stages.position;
            obj.cursor_x = startingPos(1);
            obj.cursor_y = startingPos(2);
            
            x_ROI = linspace(managers.Imaging.ROI(1,1),managers.Imaging.ROI(1,2),managers.Imaging.active_module.resolution(1));
            y_ROI = linspace(managers.Imaging.ROI(2,1),managers.Imaging.ROI(2,2),managers.Imaging.active_module.resolution(2));
            
            
            if obj.center_wl ~= obj.Spectrometer.com('Spectrometer','get_center_wavelength')
                obj.setWrapper('set_center_wavelength', obj.center_wl)
            end
            
            if obj.exposure ~= obj.Spectrometer.com('Spectrometer','get_exposure_time')
                obj.setWrapper('set_exposure_time', obj.exposure)
            end
            
            try
                temp = obj.Spectrometer.com('Spectrometer','acquire');
                obj.data.x = temp(2,:);  %obj.Spectrometer.com('Spectrometer','calibrate2'); 
                obj.data.y = temp(1,:); %obj.Spectrometer.com('Spectrometer','acquire2'); 
                
                obj.data.center_wl = obj.center_wl;
                obj.data.exposure = obj.exposure;
                obj.data.cursor_x = obj.cursor_x;
                obj.data.cursor_y = obj.cursor_y;
                                obj.data.flake =obj.flake;
                obj.data.emitter=obj.emitter;
                obj.data.x_ROI = x_ROI;
                obj.data.y_ROI = y_ROI;

                
            if ~isempty(obj.data)
                plot(ax,obj.data.x, obj.data.y,'Color',[0,.25,.25])
                xlabel(ax,'Wavelength (nm)')
                ylabel(ax,'Intensity (AU)')
                set(status,'string','Complete!')
            else
                set(status,'string','Unknown error. WinSpec did not return anything.')
            end
            catch err
            end
            % CLEAN UP CODE %
            if exist('err','var')
                % HANDLE ERROR CODE %
                rethrow(err)
            end

        end
        
        function dat = GetData(obj, ~, ~)
            dat = obj.data;
        end

        function delete(obj)
            delete(obj.listeners)
            delete(obj.Spectrometer)
        end
        
        %this abort function does not work. It'd not even real
        function abort(obj)

        end
            
        % Experimental Set methods
        function setWrapper(obj,param,varargin)
            obj.Spectrometer.com('Spectrometer',param, varargin);
            pause(1)
        end
        
        function set.center_wl(obj,val)
            obj.setWrapper('set_center_wavelength', val)
            obj.center_wl = val;
        end

        function set.exposure(obj,val)
            obj.setWrapper('set_exposure_time', val)
            obj.exposure = val;
        end
          
        
    end
end
