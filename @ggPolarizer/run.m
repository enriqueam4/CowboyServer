function run( obj,status,managers,ax )
    % Main run method (callback for CC run button)
    obj.abort_request = false;
    status.String = 'Experiment started';
    drawnow;
    % Edit here down (save data to obj.data)
    % Tips:
    % - If using a loop, it is good practice to call:
    %     drawnow; assert(~obj.abort_request,'User aborted.');
    %     as frequently as possible
    % - try/catch/end statements useful for cleaning up
    % - You can get a figure-like object (to create subplots) by:
    %     panel = ax.Parent; delete(ax);
    %     ax(1) = subplot(1,2,1,'parent',panel);
    % - drawnow can be used to update status box message and any plots

    % Edit this to include meta data for this experimental run (saved in obj.GetData)
    obj.meta.prefs = obj.prefs2struct;
    obj.meta.position = managers.Stages.position; % Save current stage position (x,y,z);
    try
        obj.server.com('kinesis','move_to', obj.starting_position)
        data.starting_position = obj.starting_position;
        data.stopping_position = obj.stopping_position;
        data.n_points = obj.n_points;
        data.integration_time = obj.integration_time
        step_size = (obj.stopping_position - obj.starting_position)/obj.n_points;
        angle_array = zeros(1,obj.n_points);
        pl_array = zeros(1,obj.n_points); 
        for i = 1:int32(obj.n_points)
            assert(~obj.abort_request,'User aborted.')
            position = i * step_size;
            disp("Moving to position "+num2str(position))
            obj.server.com('kinesis','move_to', position);
            angle_array(i) = obj.server.com('kinesis','return_position');
            disp("Measured Position: "+num2str(angle_array(i)))
            pl_array(i) =  obj.singleShot(obj.integration_time,1);         
        end
        data.angle_array = angle_array;
        data.pl_array = pl_array;
        obj.data = data;
        
        panel = ax.Parent; delete(ax)

        pax = polaraxes(panel);
        if ~isempty(obj.data)
            ps = polarscatter(pax,deg2rad(data.angle_array),data.pl_array,'filled');
            %ps.MarkerFaceColor = 'yellow';
            %set(pax,'Color',[0.5 0.5 0.5]);
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
