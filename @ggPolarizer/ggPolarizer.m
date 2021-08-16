classdef ggPolarizer < Modules.Experiment
    %ggPolarizer Description of experiment
    % Useful to list any dependencies here too

    properties(SetObservable,AbortSet)
        % These should be preferences you want set in default settings method
        starting_position = 0  
        stopping_position = 1
        n_points = 2  
        integration_time = 2
        ip = '10.16.0.182'
    end
    properties
        prefs = {'starting_position','stopping_position','n_points','integration_time',};  % String representation of desired prefs
        %show_prefs = {};   % Use for ordering and/or selecting which prefs to show in GUI
        %readonly_prefs = {}; % CC will leave these as disabled in GUI (if in prefs/show_prefs)
    end
    properties(SetAccess=private,Hidden)
        % Internal properties that should not be accessible by command line
        % Advanced users should feel free to alter these properties (keep in mind methods: abort, GetData)
        data = [] % Useful for saving data from run method
        meta = [] % Useful to store meta data in run method
        abort_request = false; % Flag that will be set to true upon abort. Use in run method!
        server;
        timerH                  % Handle to timer
        PulseTrainH             % NIDAQ task PulseTrain
        CounterH                % NIDAQ task Counter

    end
    properties(SetAccess=immutable)
        nidaq                   % Nidaq handle
        lineIn                  % DAQ input line
        lineOut                 % External Sync
    end
%obj.counter = Drivers.Counter.instance('APD1','CounterSync');
    methods(Static)
        % Static instance method is how to call this experiment
        % This is a separate file
        obj = instance()
    end
    
    methods(Access=private)
        function obj = ggPolarizer()
            % Constructor (should not be accessible to command line!)
            obj.nidaq = Drivers.NIDAQ.dev.instance('Dev1');
            obj.lineIn = 'APD1';         %%
            obj.lineOut = 'CounterSync'; %% These are hardcoded bc i am bad >:(
            lines = {obj.lineIn,obj.lineOut};
            types = {'in','out'};
            msg = {};
            for i = 1:numel(lines)
                try
                    obj.nidaq.getLines(lines{i},types{i});
                catch err
                    msg{end+1} = err.message;
                end
            end
            if ~isempty(msg)
                obj.nidaq.view;
                error('Add lines below, and load again.\n%s',strjoin(msg,'\n'))
            end


            obj.server = hwserver(obj.ip);
            obj.loadPrefs; % Load prefs specified as obj.prefs
        end    
        function stopTimer(obj,varargin)
            if isvalid(obj)
                stop(obj.timerH);
                delete(obj.timerH);
                obj.timerH = [];
                obj.CounterH.Clear;
                obj.PulseTrainH.Clear;
                obj.callback = [];
            end
        end
        function cps(obj,varargin)
            % Reads Counter Task
            if ~isvalid(obj.CounterH)
                obj.stopTimer()
            end
            nsamples = obj.CounterH.AvailableSamples;
            if nsamples
                counts = mean(diff(obj.CounterH.ReadCounter(nsamples)));
                counts = counts/(obj.dwell/1000);
                obj.callback(counts,nsamples)
            end
        end
    end

    methods
        run(obj,status,managers,ax) % Main run method in separate file

        function abort(obj)
            % Callback for when user presses abort in CC
            obj.abort_request = true;
        end
        

        function dat = GetData(obj,stageManager,imagingManager)
            % Callback for saving methods
            meta = stageManager.position;
            dat.data = obj.data;
            dat.meta = obj.meta;
        end

        % Set methods allow validating property/pref set values
        function set.starting_position(obj,val)
            assert(isnumeric(val),'Value must be numeric!')
            obj.pref1 = val;
        end
        
        function set.stopping_position(obj,val)
            assert(isnumeric(val),'Value must be numeric!')
            obj.stopping_position = val;
        end
        
        function set.n_points(obj,val)
            assert(isnumeric(val),'Value must be numeric!')
            obj.n_points = val;
        end
        
        function set.integration_time(obj,val)
            assert(isnumeric(val),'Value must be numeric!')
            obj.integration_time = val;
        end
        %%%///////////////////////////////////////////////////////%%%
        function delete(obj)
            obj.reset;
            if ~isempty(obj.fig)&&isvalid(obj.fig)
                delete(obj.fig)
            end
        end
        function data = singleShot(obj,dwell,nsamples)
            % Blocking function that will take nsamples, each with the
            % specified dwell time.
            % Returns array of size 1x(nsamples).
            % dwell is in ms.
            if nargin < 3
                nsamples = 1;
            end
            assert(nsamples>0,'Number of samples must be greater than 0.')
            nsamples = nsamples + 1;
            dwell = dwell/1000; % ms to s
            % Configure clock (pulse train)
            PulseTrainH = obj.nidaq.CreateTask('Counter singleShot PulseTrain'); %#ok<*PROPLC>
            f = 1/dwell;
            PulseTrainH.ConfigurePulseTrainOut(obj.lineOut,f,nsamples);
            % Configure Counter
            try
                CounterH = obj.nidaq.CreateTask('Counter CounterObj');
            catch err
                PulseTrainH.Clear;
                rethrow(err)
            end
            try
            CounterH.ConfigureCounterIn(obj.lineIn,nsamples,PulseTrainH);
            % Start counter (waits for pulse train), then start pulse train
            CounterH.Start;
            PulseTrainH.Start;
            catch err
                PulseTrainH.Clear;
                CounterH.Clear;
                rethrow(err)
            end
            % Wait until finished, then read data.
            PulseTrainH.WaitUntilTaskDone;
            data = CounterH.ReadCounter(CounterH.AvailableSamples);
            data = diff(data)/dwell;
            PulseTrainH.Clear;
            CounterH.Clear;
        end
        function start(obj,Callback)
            % Callback will be called every update_rate with first argument
            % is cps, second argument is number of samples read.
            % If no callback is used, a default one will be used.
            if nargin < 2
                if isempty(obj.fig)
                    obj.view;
                else
                    figure(obj.fig);  % Bring to foreground
                end
                Callback = @obj.updateView;
            end
            if ~isempty(obj.timerH)
                return  % Silently fail
            end
            obj.timerH = timer('ExecutionMode','fixedRate','name','Counter',...
                'period',obj.update_rate,'timerfcn',@obj.cps);
            obj.callback = Callback;
            dwell = obj.dwell/1000; % ms to s
            obj.PulseTrainH = obj.nidaq.CreateTask('Counter PulseTrain');
            f = 1/dwell; %#ok<*PROP>
            try
                obj.PulseTrainH.ConfigurePulseTrainOut(obj.lineOut,f);
            catch err
                obj.reset
                rethrow(err)
            end
            obj.CounterH = obj.nidaq.CreateTask('Counter CounterObj');
            try
                continuous = true;
                buffer = f*obj.update_rate;
                obj.CounterH.ConfigureCounterIn(obj.lineIn,buffer,obj.PulseTrainH,continuous)
            catch err
                obj.reset
                rethrow(err)
            end
            obj.PulseTrainH.Start;
            obj.CounterH.Start;
            start(obj.timerH)
        end
        
        function stop(obj)
            if ~isempty(obj.timerH)
                obj.stopTimer()
            end
        end
        function reset(obj)
            if ~isempty(obj.timerH)
                if isvalid(obj.timerH)&&strcmp(obj.timerH.Running,'on')
                    obj.stopTimer()
                end
                obj.timerH = [];
            else
                if ~isempty(obj.CounterH)&&isvalid(obj.CounterH)
                    obj.CounterH.Clear;
                end
                if ~isempty(obj.PulseTrainH)&&isvalid(obj.PulseTrainH)
                    obj.PulseTrainH.Clear
                end
            end
        end

        
    end
end
