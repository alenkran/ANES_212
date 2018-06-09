import numpy as np
from scipy import signal

def check_columns_consistent(df_dict):
	for idx, key in enumerate(df_dict):
		value = df_dict[key]
		if idx == 0:
			start_col = value.columns.values
		else:
			next_col = value.columns.values
			if not np.array_equal(start_col, next_col):
				return False
	return True

def sxx_sliding_window(Sxx, t, seizure, seizure_time, num_ch, sliding=True, width=16, all=False):
	# Window size is going to be 16x64 (time vs frequency)
	if not all:
		height = 32*32/width
	else:
		height = Sxx.shape[1]
	height = int(height)

	if sliding:
		num_sample = Sxx.shape[-1]-width+1
	else:
		num_sample = int((Sxx.shape[-1]-width+1)/width)
	ndim = Sxx.ndim
	Sxx_window = np.zeros((num_sample,num_ch,height,width))
	label = np.zeros((num_sample,1))
	
	idx_list = range(Sxx.shape[-1]-width+1)
	if not sliding:
		idx_list = idx_list[::width]
		idx_list = idx_list[:num_sample]

	for count, i in enumerate(idx_list):
		if ndim == 2:
			Sxx_window[count,:,:,:] = Sxx[0:height,i:i+width]
		else:
			Sxx_window[count,:,:,:] = Sxx[:,0:height,i:i+width]
		t_start, t_end = t[i], t[i+width-1]
		label[count] = sum(seizure[(seizure_time >= t_start) & (seizure_time <= t_end)])
	return Sxx_window, label


def df_to_spectrogram_FT(df_dict, sliding=True, avg=False, npserseg=512, noverlap=0, width=16, stft = True):
	# Check the data is good (columns are consistent, etc)
	assert(check_columns_consistent(df_dict))
	height = 32*32/width # Maybe fix this one day?
	fs = 256.0
	if avg:
		num_ch = 1
	else:
		num_ch = list(df_dict.values())[0].as_matrix().shape[1]-3

	spect_window = np.zeros((0,num_ch,int(height),int(width)), dtype=int)
	window_label = np.zeros((0,1))
	for key in df_dict:
		value = df_dict[key]
		temp = value.as_matrix()
		seizure = temp[:,1]
		seizure_time = temp[:,0]
		temp = temp[:,3:]
		
		# average all the chanells for now
		if avg:
			x = np.mean(temp[:,3:], axis=1)

			# Get spectrogram
			if stft:
				f, t, Sxx = signal.stft(x, fs, window='hanning', nperseg=npserseg, noverlap=noverlap)
				Sxx = np.abs(Sxx)
			else:
				f, t, Sxx = signal.spectrogram(x, fs, window='hanning', nperseg=npserseg, noverlap=noverlap)
			Sxx = 20*np.log10(Sxx)

			# Get window of spectrogram
			Sxx_window, label = sxx_sliding_window(Sxx, t, seizure, seizure_time, num_ch, sliding=sliding, width=width)
			
		else: # Watch out for weird columns re-ordering? Patient 1 is well behaved
			label_stack = np.zeros((1,0))
			for i in range(temp.shape[1]):
				x = temp[:,i]
				# Get spectrogram
				if stft:
					f, t, Sxx_temp = signal.stft(x, fs, window='hanning', nperseg=npserseg, noverlap=noverlap)
					Sxx_temp = np.abs(Sxx_temp)
				else:
					f, t, Sxx_temp = signal.spectrogram(x, fs, window='hanning', nperseg=npserseg, noverlap=noverlap)
				if i == 0:
					Sxx = np.zeros((num_ch,Sxx_temp.shape[0],Sxx_temp.shape[1]))
				Sxx[i,:,:] = 20*np.log10(Sxx_temp)
				
			# Get window of spectrogram
			Sxx_window, label = sxx_sliding_window(Sxx, t, seizure, seizure_time, num_ch, sliding=sliding, width=width)
				
		spect_window = np.vstack([spect_window, Sxx_window])
		window_label = np.vstack([window_label, label])
	spect_window[spect_window == -np.inf] = np.amin(spect_window[spect_window > -np.inf])
	spect_window[spect_window == np.inf] = np.amax(spect_window[spect_window < np.inf])
	delta_t = t[1]-t[0]
	return spect_window, window_label, delta_t

def df_to_spectrogram_2D(df_dict, sliding=True, noverlap=0, nperseg=512, stft = True):
	# Check the data is good (columns are consistent, etc)
	assert(check_columns_consistent(df_dict))
	fs = 256.0
	num_ch = df_dict.values()[0].as_matrix().shape[1]-3
	height = int(fs)+1

	spect_window = np.zeros((0,num_ch,height))
	window_label = np.zeros((0,1))
	for key in df_dict:
		value = df_dict[key]
		temp = value.as_matrix()
		seizure = temp[:,1]
		seizure_time = temp[:,0]
		temp = temp[:,3:]
		
		label_stack = np.zeros((1,0))
		for i in range(temp.shape[1]):
			x = temp[:,i]
			# Get spectrogram
			if stft:
				f, t, Sxx_temp = signal.stft(x, fs, window='hanning', nperseg=nperseg, noverlap=noverlap)
				Sxx_temp = np.abs(Sxx_temp)
			else:
				f, t, Sxx_temp = signal.spectrogram(x, fs, window='hanning', nperseg=nperseg, noverlap=noverlap)
			if i == 0:
				Sxx = np.zeros((num_ch,Sxx_temp.shape[0],Sxx_temp.shape[1]))
			Sxx[i,:,:] = 20*np.log10(Sxx_temp)

		# Get window of spectrogram
		Sxx_window, label = sxx_sliding_window(Sxx, t, seizure, seizure_time, num_ch, sliding=False, width=1, all=True)
		Sxx_window = np.squeeze(Sxx_window)
		spect_window = np.vstack([spect_window, Sxx_window])
		window_label = np.vstack([window_label, label])
	spect_window[spect_window == -np.inf] = np.amin(spect_window[spect_window > -np.inf])
	spect_window[spect_window == np.inf] = np.amax(spect_window[spect_window < np.inf])
	delta_t = t[1]-t[0]
	return spect_window, window_label, delta_t

def error_to_spectrogram_2D(df_dict, sliding=True, noverlap=0, nperseg=512, stft = True):
	# Check the data is good (columns are consistent, etc)
	fs = 256.0
	num_ch = 1
	height = int(fs)+1

	spect_window = np.zeros((0,height))
	window_label = np.zeros((0,1))
	for key in df_dict:
		temp = df_dict[key]
		seizure = temp[:,1]
		seizure_time = temp[:,0]
		x = np.squeeze(temp[:,2:])
		
		# Get spectrogram
		if stft:
			f, t, Sxx_temp = signal.stft(x, fs, window='hanning', nperseg=nperseg, noverlap=noverlap)
			Sxx_temp = np.abs(Sxx_temp)
		else:
			f, t, Sxx_temp = signal.spectrogram(x, fs, window='hanning', nperseg=nperseg, noverlap=noverlap)
		Sxx = 20*np.log10(Sxx_temp)
		Sxx = Sxx.reshape((1,Sxx.shape[0],Sxx.shape[1]))
		# Get window of spectrogram
		Sxx_window, label = sxx_sliding_window(Sxx, t, seizure, seizure_time, num_ch, sliding=False, width=1, all=True)
		Sxx_window = np.squeeze(Sxx_window)

		spect_window = np.vstack([spect_window, Sxx_window])
		window_label = np.vstack([window_label, label])
	spect_window[spect_window == -np.inf] = np.amin(spect_window[spect_window > -np.inf])
	spect_window[spect_window == np.inf] = np.amax(spect_window[spect_window < np.inf])
	delta_t = t[1]-t[0]
	return spect_window, window_label, delta_t