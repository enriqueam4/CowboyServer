classdef ggSpectralScan < Modules.Experiment
    properties
        data
        spec
        meta
        prefs = {'ip'};
        show_prefs = {'exposure','position','grating','ip'};
    end
    properties(SetObservable,AbortSet)
        ip = '10.16.0.182';
        grating = '';
        position = 620;       % Grating position
        exposure = 1000;         % Seconds
    end
    properties(SetAccess=private,Hidden)
        Spectrometer
        listeners
        scanH;  
    end
    properties(Access=private)
        abort_request = false;  % Request flag for abort
    end
    
    methods(Access=private)
         function obj = ggSpectralScan()
            %obj.path = 'spectrometer';
            obj.Spectrometer = hwserver(obj.ip);
            obj.position = obj.Spectrometer.com('Spectrometer','get_center_wavelength');
            obj.exposure = obj.Spectrometer.com('Spectrometer','get_exposure_time');
            obj.grating = obj.Spectrometer.com('Spectrometer','get_grating');
            obj.data = [];
            obj.spec = [];
            
            try
                obj.loadPrefs; % Load prefs should load WinSpec via set.ip
            catch err % Don't need to raise alert here
                if ~strcmp(err.message,'Spectrometer not set')
                    rethrow(err)
                end
            end
         end
         % probably dont need a setWinSpec function here
     end
    methods(Static)
        function obj = instance()
            mlock;
            persistent Object
            if isempty(Object) || ~isvalid(Object)
                Object = Experiments.ggSpectralScan();
            end
            obj = Object;
        end
    end
    methods
        function run(obj,statusH,managers,ax)
            
            obj.Spectrometer = hwserver(obj.ip);
            obj.abort_request = false;
            assert(~isempty(obj.Spectrometer)&&isobject(obj.Spectrometer)&&isvalid(obj.Spectrometer),'Spectrometer not configured propertly; check the IP');
            
            obj.Spectrometer.com('Spectrometer','move_spe');
            
            stage = managers.Imaging.active_module.uses_stage;
            assert(logical(managers.Stages.check_module_str(stage)),'Stage associated with active imager is not loaded.');
            managers.Stages.setActiveModule(stage); % Make the stage active
            startingPos = managers.Stages.position;
            zpos = startingPos(3);
            
            x = linspace(managers.Imaging.ROI(1,1),managers.Imaging.ROI(1,2),managers.Imaging.active_module.resolution(1));
            y = linspace(managers.Imaging.ROI(2,1),managers.Imaging.ROI(2,2),managers.Imaging.active_module.resolution(2));
            % Need to take a scan to see how long it is
            temp_exp = obj.exposure;
            obj.setWrapper('set_exposure_time', 1) % Temporary to grab frame
            calibration = obj.Spectrometer.com('Spectrometer','acquire');
            obj.spec.x = calibration(2,:);
            obj.spec.y = calibration(1,:);
            plot(obj.spec.x,obj.spec.y,'parent',ax); 
            title(ax,'Test with msec exposure');
            obj.setWrapper('set_exposure_time',temp_exp)
            set(statusH,'string','Allocating Memory...'); drawnow;
            obj.data.x = x;
            obj.data.y = y;
            obj.data.freq = obj.spec.x;
            obj.data.scan = obj.spec.y;
            obj.data.meta.ExposureSec = temp_exp;
            restart = true;

            if isfield(obj.data,'scan') && sum(isnan(obj.data.scan(:))) && obj.data.meta.ExposureSec==temp_exp
                start = numel(obj.data.scan(:,:,1)) - sum(sum(isnan(obj.data.scan(:,:,1))));
                answer = questdlg('Detected incomplete scan. Do you want to resume or start over?','Run','Resume','Restart','Resume');
                if isempty(answer) % User closed window, so let's take that as an abort
                    managers.Experiment.abort; drawnow;
                elseif strcmp(answer,'Resume')
                    restart = false;
                end
            end
            assert(~obj.abort_request,'User Aborted.')
            if restart
                start = 0;
                obj.data.scan = NaN([fliplr(managers.Imaging.active_module.resolution), length(obj.spec.x)]);
            end
            
            obj.data.meta = obj.spec; % Grab everything from sample SPE file
            obj.data.meta.ExposureSec = temp_exp; % Overwrite real exposure time
            obj.scanH = imagesc(x,y,NaN(fliplr(managers.Imaging.active_module.resolution)),'parent',managers.handles.axImage);
            set(managers.handles.axImage,'ydir','normal');
            axis(obj.scanH.Parent,'image');
            spectH = plot(NaN,NaN,'parent',ax);
            xlabel(ax,'Wavelength (nm)');
            ylabel(ax,'Counts (a.u.)');
            
            set(obj.scanH,'ButtonDownFcn',@(a,b)obj.moveTo(a,b,spectH));
            dt = NaN;
            total = length(x)*length(y);
            err = [];
            % good to here - - - - - -
            try
            for i = 1:length(y)
                for j = 1:length(x)
                    if j+(i-1)*length(y) <= start
                        continue
                    end
                    assert(~obj.abort_request,'User Aborted.')
                    tic;
                    % Update time estimate
                    n = (i-1)*length(y)+j;
                    hrs = floor(dt*(total-n)/60/60);
                    mins = round((dt*(total-n)-hrs*60*60)/60);
                    msg = sprintf('Running (%i%%)\n%i hrs %i mins left.',round(100*n/total),hrs,mins);
                    set(statusH,'string',msg); drawnow;
                    % Move to next spot and take spectra
                    managers.Stages.move([x(j),y(i),zpos]);
                    managers.Stages.waitUntilStopped;
                    try
                        temp = obj.Spectrometer.com('Spectrometer','acquire');
                        obj.spec.y = temp(1,:);
                        % Update data structures and plots
                        obj.data.scan(i,j,:) = obj.spec.y;
                        set(spectH,'xdata',obj.spec.x,'ydata',obj.spec.y);
                        title(ax,sprintf('Spectra %i of %i',n,total));
                        set(obj.scanH,'cdata',mean(obj.data.scan,3));
                        drawnow;
                    catch err
                        warning('Problem using functio.  Assigning a value of 0.');
                        temp = 0;
                        obj.spec.y = temp;
                        obj.spec.x = temp;
                        set(spectH,'xdata',obj.spec.x,'ydata',obj.spec.y);
                        title(ax,sprintf('Spectra %i of %i',n,total));
                        set(obj.scanH,'cdata',mean(obj.data.scan,3));
                    end
                    
                    if isnan(dt)
                        dt = toc;
                    else
                        dt = 0.5*dt+0.5*toc;
                    end
                end
            end
            
            catch err
            end
            managers.Stages.move(startingPos)
            managers.Stages.waitUntilStopped;
            if ~isempty(err)
                rethrow(err)
            end
            obj.meta = obj.prefs2struct;
            obj.meta.imager.name = class(managers.Imaging.active_module);
            obj.meta.imager.prefs = managers.Imaging.active_module.prefs2struct;
            obj.meta.stage.name = class(managers.Stages.active_module);
            obj.meta.stage.prefs = managers.Stages.active_module.prefs2struct;
        end
        
        
        function moveTo(obj,hObj,eventdata,spectH)
            D = [mean(diff(hObj.XData)) mean(diff(hObj.YData))];
            xBin = ceil(eventdata.IntersectionPoint(1)/D(1)-hObj.XData(1)/D(1)+0.5);
            yBin = ceil(eventdata.IntersectionPoint(2)/D(2)-hObj.YData(1)/D(2)+0.5);
            hold(hObj.Parent,'on')
            title(spectH.Parent,sprintf('(%i,%i)',xBin,yBin));
            set(spectH,'ydata',squeeze(obj.data.scan(yBin,xBin,:)));
        end
        function dat = GetData(obj, ~, ~)
            dat = obj.data;
            dat.meta = obj.meta;
        end
        %dont need set ip function
        function delete(obj)
            delete(obj.listeners)
            delete(obj.Spectrometer)
        end
        function abort(obj)
            obj.abort_request = true;
        end
        function setWrapper(obj,param,varargin)
            obj.Spectrometer.com('Spectrometer',param, varargin);
            pause(1)
        end
        %dont need set grating function
        function set.position(obj,val)
            obj.setWrapper('set_center_wavelength', val)
            obj.position = val;
        end
        function set.exposure(obj,val)
            obj.setWrapper('set_exposure_time', val)
            obj.exposure = val;
        end
    end
end
