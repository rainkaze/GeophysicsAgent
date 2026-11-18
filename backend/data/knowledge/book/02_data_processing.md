# 2 Geophysical data processing

> An Introduction to Geophysical Exploration（地球物理勘探导论，3rd ed., Kearey, Brooks & Hill, 2002）第 2 章，印刷页 8–20。
> 页码标记 [p.N] 指书的印刷页码（PDF 页码 = 印刷页码 + 13）。

[p.8]

### 2.1 Introduction

Geophysical surveys measure the variation of some physical quantity, with respect either to position or to time. The quantity may, for example, be the strength of the Earth's magnetic field along a profile across an igneous intrusion. It may be the motion of the ground surface as a function of time associated with the passage of seismic waves. In either case, the simplest way to present the data is to plot a graph (Fig. 2.1) showing the variation of the measured quantity with respect to distance or time as appropriate.

[p.8] The graph will show some more or less complex waveform shape, which will reflect physical variations in the underlying geology, superimposed on unwanted variations from non-geological features (such as the effect of electrical power cables in the magnetic example, or vibration from passing traffic for the seismic case), instrumental inaccuracy and data collection errors. The detailed shape of the waveform may be uncertain due to the difficulty in interpolating the curve between widely spaced stations. The geophysicist's task is to separate the 'signal'from the 'noise'and interpret the signal in terms of ground structure. Analysis of waveforms such as these represents an essential aspect of geophysical data processing and interpretation.

[p.8] The fundamental physics and mathematics of such analysis is not novel, most having been discovered in the 19th or early 20th centuries. The use of these ideas is also widespread in other technological areas such as radio, television, sound and video recording, radioastronomy, meteorology and medical imaging, as well as military applications such as radar, sonar and satellite imaging. Before the general availability of digital computing, the quantity of data and the complexity of the processing severely restricted the use of the known techniques. This no longer applies and nearly all the techniques described in this chapter may be implemented in standard computer spreadsheet programs.

[p.8] The fundamental principles on which the various methods of data analysis are based are brought together in this chapter. These are accompanied by a discussion of the techniques of digital data processing by computer that are routinely used by geophysicists. Throughout this chapter, waveforms are referred to as functions of time, but all the principles discussed are equally applicable to functions of distance. In the latter case, frequency (number of waveform cycles per unit time) is replaced by spatial frequency or wavenumber (number of waveform cycles per unit distance).

### 2.2 Digitization of geophysical data

[p.8] Waveforms of geophysical interest are generally continuous (analogue) functions of time or distance. To apply the power of digital computers to the task of analysis, the data need to be expressed in digital form, whatever the form in which they were originally recorded. A continuous, smooth function of time or distance can be expressed digitally by sampling the function at a fixed interval and recording the instantaneous value of the function at each sampling point. Thus, the analogue function of time f(t) shown in Fig. 2.2(a) can be represented as the digital function g(t) shown in Fig. 2.2(b) in which the continuous function has been replaced by a series of discrete values at fixed, equal, intervals of time.

[p.8] This process is inherent in many geophysical surveys, where readings are taken of the value of some parameter (e.g. magnetic field strength) at points along survey lines. The extent to which the digital values faithfully represent the original waveform will depend on the accuracy of the amplitude measurement and the intervals between measured samples. Stated more formally, these two parameters of a digitizing system are the sampling precision (dynamic range) and the sampling frequency. Dynamic rangeis an expression of the ratio of the largest measurable amplitude Amax to the smallest measurable amplitude Amin in a sampled function. The higher the

[p.9]

dynamic range, the more faithfully the amplitude variations in the analogue waveform will be represented in the digitized version of the waveform. Dynamic range is normally expressed in the decibel (dB) scale used to define electrical power ratios: the ratio of two power values P1 and P2 is given by 10log10(P1/P2) dB. Since power is proportional to the square of signal amplitude A (2.1) Thus, if a digital sampling scheme measures amplitudes over the range from 1 to 1024 units of amplitude, the dynamic range is given by In digital computers, digital samples are expressed in binary form (i.e. they are composed of a sequence of digits that have the value of either 0 or 1).

[p.9] Each binary digit is known as a bit and the sequence of bits representing the sample value is known as a word. The number of bits in each word determines the dynamic range of a digitized waveform. For example, a dynamic range of 60dB requires 11-bit words since the appropriate amplitude ratio of 1024 ( = 210) is rendered as 10000000000 in binary form. A dynamic range of 84 dB represents an amplitude ratio of 2 14 and, hence, requires sampling with 15-bit words. Thus, increasing the number of bits in each word in digital sampling increases the dynamic range of the digital function. Sampling frequencyis the number of sampling points in unit time or unit distance.

[p.9] Intuitively, it may appear that the digital sampling of a continuous function inevitably leads to a loss of information in the resultant digital function, since the latter is only specified by discrete values at a series of points. Again intuitively, there will be no 20 20 1024 6010 10log logmax minAA()=ªdB 10 10 10 1 2 10 1 2 10 1 2 log log log PP AA AA ( ) = ( ) = ( ) 0 1020304050 Distance (m) (a) –5 –10 10 20 30 40 50 60 70 80 Time (milliseconds)(b) Ground velocity (10-6 m/s) Magnetic field (nT)

[p.9] Fig. 2.1 (a) A graph showing a typical magnetic field strength variation which may be measured along a profile. (b) A graph of a typical seismogram, showing variation of particle velocities in the ground as a function of time during the passage of a seismic wave. 1.0 –1.0 f (t) g(t) 1.0 –1.0 t t (a) (b) 0.5 0.9 1.0 0.9 0.5 0.0 –0.5 –0.9 –1.0 –0.9 –0.5 τ 2τ 3τ

[p.9] Fig. 2.2 (a) Analogue representation of a sinusoidal function. (b) Digital representation of the same function.

[p.10]

significant loss of information content as long as the frequency of sampling is much higher than the highest frequency component in the sampled function. Mathematically, it can be proved that, if the waveform is a sine curve, this can always be reconstructed provided that there are a minimum of two samples per period of the sine wave. Thus, if a waveform is sampled every two milliseconds (sampling interval), the sampling frequency is 500 samples per second (or 500Hz). Sampling at this rate will preserve all frequencies up to 250Hz in the sampled function. This frequency of half the sampling frequency is known as the Nyquist frequency (fN) and the Nyquist interval is the frequency range from zero up to fN (2.2) where Dt = sampling interval.

[p.10] If frequencies above the Nyquist frequency are present in the sampled function, a serious form of distortion results known as aliasing, in which the higher frequency components are 'folded back' into the Nyquist interval. Consider the example illustrated in Fig. 2.3 in which sine waves at different frequencies are sampled. The lower frequency wave (Fig. 2.3(a)) is accurately reproduced, but the higher frequency wave (Fig. 2.3(b), solid line) is rendered as a fictitious frequency, shown by the dashed line, within the Nyquist interval. The relationship between input and output frequencies in the case of a sampling frequency of 500Hz is shown in Fig. 2.3(c).

[p.10] It is apparent that an input frequency of 125Hz, for example, is retained in the output but that an input frequency of 625Hz is folded back to be output at 125 Hz also. To overcome the problem of aliasing, the sampling frequency must be at least twice as high as the highest frequency component present in the sampled function. If the function does contain frequencies above the Nyquist frequency determined by the sampling, it must be passed through an antialias filter prior to digitization. The antialias filter is a low-pass frequency filter with a sharp cut-off that removes frequency components above the Nyquist frequency, or attenuates them to an insignificant amplitude level.

### 2.3 Spectral analysis

[p.10] An important mathematical distinction exists between periodic waveforms(Fig. 2.4(a)), that repeat themselves at a fixed time period T, and transient waveforms(Fig. 2.4(b)), fN = ( )12Dt that are non-repetitive. By means of the mathematical technique of Fourier analysis any periodic waveform, however complex, may be decomposed into a series of sine (or cosine) waves whose frequencies are integer multiples of the basic repetition frequency 1/T, known as the fundamental frequency. The higher frequency components, at frequencies of n/T (n = 1, 2, 3, . . .), are known as harmonics. The complex waveform of Fig. 2.5(a) is built up from the addition of the two individual sine wave components shown.

[p.10] To express any waveform in terms of its constituent sine wave components, it is necessary to define not only the frequency of each component but also its amplitude and phase. If in the above example the relative amplitude and phase relations of the individual sine waves are altered, summation can (a) (b) 4fN3fN2fNfN 125 250 500 625 750 1000 Input frequency (Hz) (c)Output frequency (Hz)

[p.10] Fig. 2.3 (a) Sine wave frequency less than Nyquist frequency. (b) Sine wave frequency greater than Nyquist frequency (solid line) showing the fictitious frequency that is generated by aliasing (dashed line). (c) Relationship between input and output frequencies for a sampling frequency of 500 Hz (Nyquist frequency fN = 250 Hz).

[p.11]

produce the quite different waveform illustrated in

[p.11] Fig. 2.5(b). From the above it follows that a periodic waveform can be expressed in two different ways: in the familiar time domain, expressing wave amplitude as a function of time, or in the frequency domain, expressing the amplitude and phase of its constituent sine waves as a function of frequency. The waveforms shown in Fig. 2.5(a) and (b) are represented in Fig. 2.6(a) and (b) in terms of their amplitude and phase spectra. These spectra, known as line spectra, are composed of a series of discrete values of the amplitude and phase components of the waveform at set frequency values distributed between 0Hz and the Nyquist frequency. Transient waveforms do not repeat themselves; that is, they have an infinitely long period.

[p.11] They may be regarded, by analogy with a periodic waveform, as having an infinitesimally small fundamental frequency (1/T Æ 0) and, consequently, harmonics that occur at infinitesimally small frequency intervals to give continuous amplitude and phase spectra rather than the line spectra of periodic waveforms. However, it is impossible to cope analytically with a spectrum containing an infinite number of sine wave components. Digitization of the waveform in the time domain (Section 2.2) provides a means of dealing with the continuous spectra of transient waveforms. A digitally sampled transient waveform has its amplitude and phase spectra subdivided into a number of T (a) (b)

[p.11] Fig. 2.4 (a) Periodic and (b) transient waveforms. (a) (b)

[p.11] Fig. 2.5 Complex waveforms resulting from the summation of two sine wave components of frequency f and 2f. (a) The two sine wave components are of equal amplitude and in phase. (b) The higher frequency component has twice the amplitude of the lower frequency component and is p/2 out of phase. (After Anstey 1965.) π/2 –π/2 π/2 –π/2 f 2f Frequency f 2f Frequency f 2f Frequency f 2f Frequency AmplitudePhase AmplitudePhase (a) (b)

[p.11] Fig. 2.6 Representation in the frequency domain of the waveforms illustrated in Fig. 2.5, showing their amplitude and phase spectra.

[p.12]

thin frequency slices, with each slice having a frequency equal to the mean frequency of the slice and an amplitude and phase proportional to the area of the slice of the appropriate spectrum (Fig. 2.7). This digital expression of a continuous spectrum in terms of a finite number of discrete frequency components provides an approximate representation in the frequency domain of a transient waveform in the time domain. Increasing the sampling frequency in the time domain not only improves the time-domain representation of the waveform, but also increases the number of frequency slices in the frequency domain and improves the accuracy of the approximation here too.

[p.12] Fourier transformation may be used to convert a time function g(t) into its equivalent amplitude and phase spectra A( f ) and f( f ), or into a complex function of frequency G( f ) known as the frequency spectrum, where (2.3) The time- and frequency-domain representations of a waveform, g(t) and G( f ), are known as a Fourier pair, represented by the notation (2.4) gt G f()´ () Gf Af f( ) = ( ) ( )eif Components of a Fourier pair are interchangeable, such that, if G( f ) is the Fourier transform of g(t), then g(t) is the Fourier transform of G( f ). Figure 2.8 illustrates Fourier pairs for various waveforms of geophysical significance.

[p.12] All the examples illustrated have zero phase spectra; that is, the individual sine wave components of the waveforms are in phase at zero time. In this case f( f ) = 0 for all values of f. Figure 2.8(a) shows a spike function (also known as a Dirac function), which is the shortest possible transient waveform. Fourier transformation shows that the spike function has a continuous frequency spectrum of constant amplitude from zero to infinity; thus, a spike function contains all frequencies from zero to infinity at equal amplitude. The 'DC bias'waveform of

[p.12] Fig. 2.8(b) has, as would be expected, a line spectrum comprising a single component at zero frequency. Note that Fig. 2.8(a) and (b) demonstrate the principle of interchangeability of Fourier pairs stated above (equation (2.4)). Figures 2.8(c) and (d) illustrate transient waveforms approximating the shape of seismic pulses, together with their amplitude spectra. Both have a bandlimited amplitude spectrum, the spectrum of narrower bandwidth being associated with the longer transient waveform. In general, the shorter a time pulse the wider is its frequency bandwidth and in the limiting case a spike pulse has an infinite bandwidth. Waveforms with zero phase spectra such as those illustrated in Fig.

[p.12] 2.8 are symmetrical about the time axis and, for any given amplitude spectrum, produce the maximum peak amplitude in the resultant waveform. If phase varies linearly with frequency, the waveform remains unchanged in shape but is displaced in time; if the phase variation with frequency is non-linear the shape of the waveform is altered. A particularly important case in seismic data processing is the phase spectrum associated with minimum delay in which there is a maximum concentration of energy at the front end of the waveform. Analysis of seismic pulses sometimes assumes that they exhibit minimum delay (see Chapter 4).

[p.12] Fourier transformation of digitized waveforms is readily programmed for computers, using a 'fast Fourier transform' (FFT) algorithm as in the Cooley–Tukey method (Brigham 1974). FFT subroutines can thus be routinely built into data processing programs in order to carry out spectral analysis of geophysical waveforms. Fourier transformation is supplied as a function to standard spreadsheets such as Microsoft Excel. Fourier transformation can be extended into two dimensions (Rayner 1971), and can thus be applied to areal distributions of data such as gravity and magnetic contour maps. Amplitude densityPhase Frequency Frequency

[p.12] Fig. 2.7 Digital representation of the continuous amplitude and phase spectra associated with a transient waveform.

[p.13]

In this case, the time variable is replaced by horizontal distance and the frequency variable by wavenumber (number of waveform cycles per unit distance). The application of two-dimensional Fourier techniques to the interpretation of potential field data is discussed in Chapters 6 and 7.

### 2.4 Waveform processing

[p.13] The principles of convolution, deconvolution and correlation form the common basis for many methods of geophysical data processing, especially in the field of seismic reflection surveying. They are introduced here in general terms and are referred to extensively in later chapters. Their importance is that they quantitatively describe how a waveform is affected by a filter. Filtering modifies a waveform by discriminating between its constituent sine wave components to alter their relative amplitudes or phase relations, or both. Most audio systems are provided with simple filters to cut down on highfrequency 'hiss', or to emphasize the low-frequency 'bass'.

[p.13] Filtering is an inherent characteristic of any system through which a signal is transmitted.

### 2.4.1 Convolution

[p.13] Convolution (Kanasewich 1981) is a mathematical operation defining the change of shape of a waveform resulting from its passage through a filter. Thus, for example, a seismic pulse generated by an explosion is altered in shape by filtering effects, both in the ground and in the recording system, so that the seismogram (the filtered output) differs significantly from the initial seismic pulse (the input). As a simple example of filtering, consider a weight suspended from the end of a vertical spring. If the top of the spring is perturbed by a sharp up-and-down movement (the input), the motion of the weight (the filtered output) is a series of damped oscillations out of phase with the initial perturbation (Fig. 2.9).

[p.13] The effect of a filter may be categorized by its impulse (a) (b) (c) (d) Time Frequency t = 0 Time domain Frequency domain

[p.13] Fig. 2.8 Fourier transform pairs for various waveforms. (a) A spike function. (b) A 'DC bias'. (c) and (d) Transient waveforms approximating seismic pulses.

[p.14]

response which is defined as the output of the filter when the input is a spike function (Fig. 2.10).The impulse response is a waveform in the time domain, but may be transformed into the frequency domain as for any other waveform. The Fourier transform of the impulse response is known as the transfer functionand this specifies the amplitude and phase response of the filter, thus defining its operation completely. The effect of a filter is described mathematically by a convolutionoperation such that, if the input signal g(t) to the filter is convolved with the impulse response f(t) of the filter, known as the convolution operator, the filtered output y(t) is obtained: (2.5) where the asterisk denotes the convolution operation.

[p.14] Figure 2.11(a) shows a spike function input to a filter whose impulse response is given in Fig. 2.11(b). Clearly the latter is also the filtered output since, by definition, the impulse response represents the output for a spike input. Figure 2.11(c) shows an input comprising two separate spike functions and the filtered output (Fig. 2.11(d)) is now the superposition of the two impulse response functions offset in time by the separation of the yt gt f t()= () ()* input spikes and scaled according to the individual spike amplitudes. Since any transient wave can be represented as a series of spike functions (Fig. 2.11(e)), the general form of a filtered output (Fig.

[p.14] 2.11(f )) can be regarded as the summation of a set of impulse responses related to a succession of spikes simulating the overall shape of the input wave. The mathematical implementation of convolution involves time inversion (or folding) of one of the functions and its progressive sliding past the other function, the individual terms in the convolved output being derived by summation of the cross-multiplication products over the overlapping parts of the two functions. In general, if gi (i = 1,2,...,m) is an input function and fj ( j = 1, 2, . . . , n) is a convolution operator, then the convolution output function yk is given by (2.6) In Fig.

[p.14] 2.12 the individual steps in the convolution process are shown for two digital functions, a double spike function given by gi = g1, g2, g3 = 2, 0, 1 and an impulse response function given by fi = f1, f2, f3, f4 = 4, 3, 2, 1, where the numbers refer to discrete amplitude values at the sampling points of the two functions. From Fig. 2.11 it can be seen that the convolved output yi = y1, y2, y3, y4, y5, y6 = 8, 6, 8, 5, 2, 1. Note that the convolved output is longer than the input waveforms; if the functions to be convolved have lengths of m and n, the convolved output has a length of (m + n - 1). The convolution of two functions in the time domain becomes increasingly laborious as the functions become longer.

[p.14] Typical geophysical applications may have functions which are each from 250 to a few thousand samples long. The same mathematical result may be obtained by transforming the functions to the frequency domain, then multiplying together equivalent frequency terms of their amplitude spectra and adding terms of their phase spectra. The resulting output amplitude and phase spectra can then be transformed back to the time domain. Thus, digital filtering can be enacted in either the time ygfk mnki i m = -Â 12 1,,..., Input displacement Output displacementW Amplitude Time Input Output

[p.14] Fig. 2.9 The principle of filtering illustrated by the perturbation of a suspended weight system.

[p.14] Fig. 2.10 The impulse response of a filter. Spike input Filter Output = Impulse response

[p.15]

(a) (b) (c) (d) (e) (f)

[p.15] Fig. 2.11 Examples of filtering. (a) A spike input. (b) Filtered output equivalent to impulse response of filter. (c) An input comprising two spikes. (d) Filtered output given by summation of two impulse response functions offset in time. (e) A complex input represented by a series of contiguous spike functions. (f) Filtered output given by the summation of a set of impulse responses. 4 321 Cross-products Sum

[p.15] Fig. 2.12 A method of calculating the convolution of two digital functions. domain or the frequency domain. With large data sets, filtering by computer is more efficiently carried out in the frequency domain since fewer mathematical operations are involved. Convolution, or its equivalent in the frequency domain, finds very wide application in geophysical data processing, notably in the digital filtering of seismic and potential field data and the construction of synthetic seismograms for comparison with field seismograms (see Chapters 4 and 6).

[p.16]

### 2.4.2 Deconvolution

Deconvolution or inverse filtering (Kanasewich 1981) is a process that counteracts a previous convolution (or filtering) action. Consider the convolution operation given in equation (2.5) y(t) is the filtered output derived by passing the input waveform g(t) through a filter of impulse response f(t). Knowing y(t) and f(t), the recovery of g(t) represents a deconvolution operation. Suppose that f¢(t) is the function that must be convolved with y(t) to recover g(t) (2.7) Substituting for y(t) as given by equation (2.5) (2.8) Now recall also that (2.9) where d(t) is a spike function (a unit amplitude spike at zero time); that is, a time function g(t) convolved with a spike function produces an unchanged convolution output function g(t).

[p.16] From equations (2.8) and (2.9) it follows that (2.10) Thus, provided the impulse response f(t) is known, f¢(t) can be derived for application in equation (2.7) to recover the input signal g(t). The function f ¢(t) represents the deconvolution operator. Deconvolution is an essential aspect of seismic data processing, being used to improve seismic records by removing the adverse filtering effects encountered by seismic waves during their passage through the ground.

[p.16] In the seismic case, referring to equation (2.5), y(t) is the seismic record resulting from the passage of a seismic wave g(t) through a portion of the Earth, which acts as a filter with an impulse response f(t).The particular problem with deconvolving a seismic record is that the input waveform g(t) and the impulse response f(t) of the Earth filter are in general unknown. Thus the 'deterministic' approach to deconvolution outlined above cannot be employed and the deconvolution operator has to be ft f t t( ) ¢( ) = ( )* d gt gt t( ) = ( ) ( )*d gt gt f t f t( ) = ( ) ( ) ¢( )** gt yt f t( ) = ( ) ¢( )* yt gt f t()= () ()* designed using statistical methods.

[p.16] This special approach to the deconvolution of seismic records, known as predictive deconvolution, is discussed further in Chapter 4.

### 2.4.3 Correlation

[p.16] Cross-correlation of two digital waveforms involves crossmultiplication of the individual waveform elements and summation of the cross-multiplication products over the common time interval of the waveforms. The crosscorrelation function involves progressively sliding one waveform past the other and, for each time shift, or lag, summing the cross-multiplication products to derive the cross-correlation as a function of lag value. The crosscorrelation operation is similar to convolution but does not involve folding of one of the waveforms. Given two digital waveforms of finite length, xi and yi (i = 1, 2, . . . , n), the cross-correlation function is given by (2.11) where t is the lag and m is known as the maximum lag value of the function.

[p.16] It can be shown that crosscorrelation in the time domain is mathematically equivalent to multiplication of amplitude spectra and subtraction of phase spectra in the frequency domain. Clearly, if two identical non-periodic waveforms are cross-correlated (Fig. 2.13) all the cross-multiplication products will sum at zero lag to give a maximum positive value. When the waveforms are displaced in time, however, the cross-multiplication products will tend to cancel out to give small values. The cross-correlation function therefore peaks at zero lag and reduces to small values at large time shifts. Two closely similar waveforms will likewise produce a cross-correlation function that is strongly peaked at zero lag.

[p.16] On the other hand, if two dissimilar waveforms are cross-correlated the sum of cross-multiplication products will always be near to zero due to the tendency for positive and negative products to cancel out at all values of lag. In fact, for two waveforms containing only random noise the cross-correlation function fxy(t) is zero for all non-zero values of t. Thus, the cross-correlation function measures the degree of similarity of waveforms. An important application of cross-correlation is in the detection of weak signals embedded in noise.

[p.16] If a waveform contains a known signal concealed in noise at unknown time, cross-correlation of the waveform with the signal function will produce a cross-correlation function ft tt t xy i i n ixy m m( ) =-<<+( )+ = - Â

[p.17]

centred on the time value at which the signal function and its concealed equivalent in the waveform are in phase (Fig. 2.14). A special case of correlation is that in which a waveform is cross-correlated with itself, to give the autocorrelation function fxx(t).This function is symmetrical about a zero lag position, so that (2.12) The autocorrelation function of a periodic waveform is also periodic, with a frequency equal to the repetition frequency of the waveform. Thus, for example, the autocorrelation function of a cosine wave is also a cosine wave. For a transient waveform, the autocorrelation function decays to small values at large values of lag.

[p.17] These differing properties of the autocorrelation function of periodic and transient waveforms determine one of its main uses in geophysical data processing, namely, the detection of hidden periodicities in any given waveform. Side lobes in the autocorrelation function (Fig. 2.15) are an indication of the existence of periodicities in the original waveform, and the spacing of the side lobes defines the repetition period. This property is particularly useful in the detection and suppression of multiple reflections in seismic records (see Chapter 4).

[p.17] ft f txx xx( ) =-( ) The autocorrelation function contains all the amplitude information of the original waveform but none of the phase information, the original phase relationships being replaced by a zero phase spectrum. In fact, the autocorrelation function and the square of the amplitude spectrum A( f ) can be shown to form a Fourier pair (2.13) Since the square of the amplitude represents the power term (energy contained in the frequency component) the autocorrelation function can be used to compute the power spectrumof a waveform.

### 2.5 Digital filtering

[p.17] In waveforms of geophysical interest, it is standard practice to consider the waveform as a combination of signal and noise. The signal is that part of the waveform that relates to the geological structures under investigation. The noise is all other components of the waveform. The noise can be further subdivided into two components, random and coherent noise. Random noise is just that, statistically ftxx Af( ) ´ ( )2 Waveform 1 Waveform 2 Cross-correlation function Zero lag – ve lag + ve lag lag

[p.17] Fig. 2.13 Cross-correlation of two identical waveforms.

[p.18]

random, and usually due to effects unconnected with the geophysical survey. Coherent noise is, on the other hand, components of the waveform which are generated by the geophysical experiment, but are of no direct interest for the geological interpretation. For example, in a seismic survey the signal might be the seismic pulse arriving at a detector after being reflected by a geological boundary at depth. Random noise would be background vibration due to wind, rain or distant traffic. Coherent noise would be the surface waves generated by the seismic source, which also travel to the detector and may obscure the desired signal.

[p.18] In favourable circumstances the signal-to-noise ratio (SNR) is high, so that the signal is readily identified and extracted for subsequent analysis. Often the SNR is low and special processing is necessary to enhance the information content of the waveforms. Different approaches are needed to remove the effect of different types of noise. Random noise can often be suppressed by repeated measurement and averaging. Coherent noise may be filtered out by identifying the particular characteristics of that noise and designing a special filter to remove it.

[p.18] The remaining signal itself may be distorted due to the effects of the recording system, and again, if the nature of the recording system is accurately known, suitable filtering can be designed. Digital filtering is widely employed in geophysical data processing to improve SNR or otherwise improve the signal characteristics. A very wide range of digital filters is in routine use in geophysical, and especially seismic, data processing (Robinson & Treitel 2000).The two main types of digital filter are frequency filters and inverse (deconvolution) filters.

### 2.5.1 Frequency filters

[p.18] Frequency filters discriminate against selected frequency components of an input waveform and may be low-pass (LP), high-pass (HP), band-pass (BP) or band-reject Waveform Signal function Cross-correlation function S1 S2 S3 Signal positions in waveform

[p.18] Fig. 2.14 Cross-correlation to detect occurrences of a known signal concealed in noise. (After Sheriff 1973.) (a) (b) φxx(τ) τ τ

[p.18] Fig. 2.15 Autocorrelation of the waveform exhibiting periodicity shown in (a) produces the autocorrelation function with side lobes shown in (b).The spacing of the side lobes defines the repetition period of the original waveform.

[p.19]

(BR) in terms of their frequency response. Frequency filters are employed when the signal and noise components of a waveform have different frequency characteristics and can therefore be separated on this basis. Analogue frequency filtering is still in widespread use and analogue antialias (LP) filters are an essential component of analogue-to-digital conversion systems (see Section 2.2). Nevertheless, digital frequency filtering by computer offers much greater flexibility of filter design and facilitates filtering of much higher performance than can be obtained with analogue filters. To illustrate the design of a digital frequency filter, consider the case of a LP filter whose cut-off frequency is fc.

[p.19] The desired output characteristics of the ideal LP filter are represented by the amplitude spectrum shown in Fig. 2.16(a).The spectrum has a constant unit amplitude between 0 and fc and zero amplitude outside this range: the filter would therefore pass all frequencies between 0 and fc without attenuation and would totally suppress frequencies above fc. This amplitude spectrum represents the transfer function of the ideal LP filter. Inverse Fourier transformation of the transfer function into the time domain yields the impulse response of the ideal LP filter (see Fig. 2.16(b)). However, this impulse response (a sinc function) is infinitely long and must therefore be truncated for practical use as a convolution operator in a digital filter.

[p.19] Figure 2.16(c) represents the frequency response of a practically realizable LP filter operator of finite length (Fig. 2.16(d)). Convolution of the input waveform with the latter will result in LP filtering with a ramped cut-off (Fig. 2.16(c)) rather than the instantaneous cut-off of the ideal LP filter. HP, BP and BR time-domain filters can be designed in a similar way by specifying a particular transfer function in the frequency domain and using this to design a finite-length impulse response function in the time domain. As with analogue filtering, digital frequency filtering generally alters the phase spectrum of the waveform and this effect may be undesirable.

[p.19] However, zero phase filters can be designed that facilitate digital filtering without altering the phase spectrum of the filtered signal.

### 2.5.2 Inverse (deconvolution) filters

[p.19] The main applications of inverse filtering to remove the adverse effects of a previous filtering operation lie in the field of seismic data processing. A discussion of inverse filtering in the context of deconvolving seismic records is given in Chapter 4.

### 2.6 Imaging and modelling

[p.19] Once the geophysical waveforms have been processed to maximize the signal content, that content must be extracted for geological interpretation. Imaging and modelling are two different strategies for this work. As the name implies, in imaging the measured wave- (a) (b) (c) (d) Sinc function Filter operator fc ft fc ft Frequency domain Time domain

[p.19] Fig. 2.16 Design of a digital low-pass filter.

[p.20]

forms themselves are presented in a form in which they simulate an image of the subsurface structure. The most obvious examples of this are in seismic reflection (Chapter 4) and ground-penetrating radar (Chapter 9) sections, where the waveform of the variation of reflected energy with time is used to derive an image related to the occurrence of geological boundaries at depth. Often magnetic surveys for shallow engineering or archaeological investigations are processed to produce shaded, coloured, or contoured maps where the shading or colour correlates with variations of magnetic field which are expected to correlate with the structures being sought.

[p.20] Imaging is a very powerful tool, as it provides a way of summarizing huge volumes of data in a format which can be readily comprehended, that is, the visual image. A disadvantage of imaging is that often it can be difficult or impossible to extract quantitative information from the image. In modelling, the geophysicist chooses a particular type of structural model of the subsurface, and uses this to predict the form of the actual waveforms recorded. The model is then adjusted to give the closest match between the predicted (modelled) and observed waveforms. The goodness of the match obtained depends on both the signal-to-noise ratio of the waveforms and the initial choice of the model used.

[p.20] The results of modelling are usually displayed as cross-sections through the structure under investigation. Modelling is an essential part of most geophysical methods and is well exemplified in gravity and magnetic interpretation (see Chapters 6 and 7).

[p.20] Problems

[p.20] 1. Over the distance between two seismic recording sites at different ranges from a seismic source, seismic waves have been attenuated by 5dB. What is the ratio of the wave amplitudes observed at the two sites? 2. In a geophysical survey, time-series data are sampled at 4ms intervals for digital recording. (a) What is the Nyquist frequency? (b) In the absence of antialias filtering, at what frequency would noise at 200Hz be aliased back into the Nyquist interval? 3. If a digital recording of a geophysical time series is required to have a dynamic range of 120dB, what number of bits is required in each binary word? 4. If the digital signal (-1, 3, -2, -1) is convolved with the filter operator (2, 3, 1), what is the convolved output? 5.

[p.20] Cross-correlate the signal function (-1, 3, -1) with the waveform (-2, -4, -4, -3, 3, 1, 2, 2) containing signal and noise, and indicate the likely position of the signal in the waveform on the basis of the cross-correlation function. 6. A waveform is composed of two in-phase components of equal amplitude at frequencies f and 3f. Draw graphs to represent the waveform in the time domain and the frequency domain.

[p.20] Further reading

[p.20] Brigham, E. O. (1974) The Fast Fourier Transform . Prentice-Hall, New Jersey. Camina, A. R. & Janacek, G. J. (1984) Mathematics for Seismic Data Processing and Interpretation. Graham & Trotman, London. Claerbout, J. F. (1985) Fundamentals of Geophysical Data Processing. McGraw-Hill, New York. Dobrin, M. B. & Savit, C. H. (1988) Introduction to Geophysical Prospecting (4th edn). McGraw-Hill, New York. Kanasewich, E. R. (1981) Time Sequence Analysis in Geophysics (3rd edn). University of Alberta Press. Kulhanek, O. (1976) Introduction to Digital Filtering in Geophysics. Elsevier, Amsterdam. Menke, W. (1989) Geophysical Data Analysis: Discrete Inverse Theory. Academic Press, London. Rayner, J. N. (1971) An Introduction to Spectral Analysis .

[p.20] Pion, England. Robinson, E. A. & Trietel, S. (2000) Geophysical Signal Analysis. Prentice-Hall, New Jersey. Sheriff, R. E. & Geldart, L. P. (1983) Exploration Seismology Vol 2: Data-Processing and Interpretation. Cambridge University Press, Cambridge.
