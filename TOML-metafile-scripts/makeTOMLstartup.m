function makeTOMLstartup(app)

    app.Data.metaFile = metaFile;
    app.Data.Experimenter = Experimenter;
    app.Data.subject = subject;
    app.Data.session = session;
    app.Data.date = Date;
    app.Data.paradigm = paradigm;
    app.Data.surgeon = surgeon;
    app.Data.surgeryDate = surgeryDate;
    app.Data.diameter = diameter;
    app.Data.behavior_offset = dT;
    app.Data.sampleFreq = sampleFreq;
    app.Data.downsampleFreq = downsampleFreq;
    app.Data.z_window = z;
    app.Data.transform = transform;
    app.Data.no_per_seg = Noperseg;
    app.Data.no_overlap = NoOverlap;
    app.Data.BP_BW = BP;
    app.Data.total_channels = total_chan;
    app.Data.rightSignal = rightSignal;
    app.Data.leftSignal = leftSignal;
    app.Data.rightInjection = rightInjection;
    app.Data.leftInjection = leftInjection;
    app.Data.rightImplant = rightImplant;
    app.Data.leftImplant = leftImplant;
    app.Data.carrierRight = carrierRight;
    app.Data.carrierLeft = carrierLeft;
    
end
