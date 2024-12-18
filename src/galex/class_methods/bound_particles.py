import numpy as np
from unyt import unyt_array, unyt_quantity
from pytreegrav import Potential
from copy import deepcopy, copy


def bound_particlesBH(pos, vel, mass, 
                      #ids = None,
                      soft = None,
                      cm = None,
                      vcm = None,
                      theta = 0.7,
                      refine = False,
                      delta = 1E-5,
                      verbose = False
                     ):
    """Computes the bound particles of a halo/ensemble of particles using the Barnes-Hut algorithm implemented in PYTREEGRAV.
    The bound particles are defined as those with E= pot + kin < 0. The center of mass position is not required, as the potential 
    calculation is done with relative distances between particles. To compute the kinetic energy of the particles the *v_cm*
    is needed: you can provide one or the function make a crude estimates of it with all particles. 

    You can ask the function to refine the unbinding by iterating until the *cm* and *v_cm* vectors converge to within a user specified
    delta (default is 1E-5, relative). This is recomended if you dont specify the *v_cm*, as the initial estimation using all particles
    may be biased for anisotropic particle distributions. If you provide your own *v_cm*, taken from somewhere reliable e.g. Rockstar halo
    catalogues, it will be good enough. Note that if you still want to refine, the *v_cm* you provided will be disregarded after the
    first iteration.

    Typical run times are of 0.5-2s dependin if the result is refined or not. This is similar to the I/O overheads of yt.load, making it reasonable for
    use with a few halos (where you dont care if the total runtime is twice as long because it will be fast enough).

    Unit handling is done with unyt. Please provide arrays as unyt_arrays.
    
    Parameters
    ----------
    pos : array
        Position of the particles, with units. When calculating, units are converted to physical kpc.
    vel : array
        Velocity of the particles in pysical km/s.
    mass : array
        Masses of particles, with units. When calculatig, they are converted to Msun.
    ids : array, optional
        Array of unique particle ids. If provided, the function returns masks for bound particles and bound particle ids.
    soft : array, optional
        Softening of particles. Not required, results do not differ a lot.
    cm : array, optional
        Placeholder. Doesnt do anything if provided.
    vcm : array, optional
        Initial Center of mass velocity estimation.
    theta : float, optional
        theta parameter fir Barnes Hut algorithm, default is 0.7.
    refine, bool, optional
        Whether to refine the undinding. Default is false.
    delta : float, optional
        Relative tolerance for determined if the unbinding is refined. Default is 1E-5.
    verbose : bool, optional
        Whether to print when running. Work in progrees. default is False.
    """

    cm = np.average(pos, axis=0, weights=mass) if cm is None else cm
    vcm = np.average(vel, axis=0, weights=mass) if vcm is None else vcm

    softenings = soft.in_units(pos.units) if soft is not None else None

    pot = Potential(pos, mass, softenings,
                    parallel=True, quadrupole=True, G=unyt_quantity(4.300917270038e-06, "kpc/Msun * (km/s)**2").in_units(pos.units/mass.units * (vel.units)**2), 
                    theta=theta)

    for i in range(100):
        abs_vel = np.sqrt( (vel[:,0]-vcm[0])**2 +
                           (vel[:,1]-vcm[1])**2 + 
                           (vel[:,2]-vcm[2])**2
                       )
    
        kin = 0.5 * mass * abs_vel**2
        
        pot = mass * unyt_array(pot, vel.units**2)
        E = kin + pot
        bound_mask = E < 0
        
        
        N = int(np.rint(np.minimum(0.1 * np.count_nonzero(bound_mask), 32)))
        most_bound_ids = np.argsort(E)[:N]
        most_bound_mask = np.zeros(len(E), dtype=bool)
        most_bound_mask[most_bound_ids] = True
        
        new_cm = np.average(pos[most_bound_mask], axis=0, weights=mass[most_bound_mask])
        new_vcm = np.average(vel[most_bound_mask], axis=0, weights=mass[most_bound_mask])        
     
        delta_cm = np.sqrt(np.sum((new_cm - cm)**2, axis=0)) / np.linalg.norm(cm) < delta
        delta_vcm =  np.sqrt(np.sum((new_vcm - vcm)**2, axis=0)) / np.linalg.norm(vcm) < delta        
        
        if not refine or (delta_cm and delta_vcm):
            return E, kin, pot
            #return (bound_mask, most_bound_mask, ids[bound_mask], ids[most_bound_mask]) if ids is not None else (bound_mask, most_bound_mask)

        cm, vcm = copy(new_cm), copy(new_vcm)



def bound_particlesAPROX(pos, vel, mass, 
                      #ids = None,
                      cm = None,
                      vcm = None,
                      refine = False,
                      delta = 1E-5,
                      verbose = False
                     ):
    """Computes the bound particles by approximating the ensemble as a point source for ease of potential calculation. 
    The bound particles are defined as those with E= pot + kin < 0. The center of mass position is required, as the potential 
    calculation is done relative to the cm position with the following expression:
    
                                                pot = -G* Mtot * m_i / |x_i - x_cm|
    
    To compute the kinetic energy of the particles the *v_cm* is needed: you can provide one or the function make a crude estimates of it with all particles. 

    You can ask the function to refine the unbinding by iterating until the *cm* and *v_cm* vectors converge to within a user specified
    delta (default is 1E-5, relative). This is recomended if you dont specify the *v_cm*, as the initial estimation using all particles
    may be biased for anisotropic particle distributions. If you provide your own *v_cm*, taken from somewhere reliable e.g. Rockstar halo
    catalogues, it will be good enough. Note that if you still want to refine, the *v_cm* you provided will be disregarded after the
    first iteration.

    Refining the unbinding is advised. This method is somewhat less reliable than its BH counterpart.

    Typical run times are of 0.01-0.05s dependin if the result is refined or not. This is much faster to the I/O overheads of yt.load, making it reasonable for
    use with a large number of halos (where you do care if the total runtime is twice as long).

    Unit handling is done with unyt. Please provide arrays as unyt_arrays.
    
    Parameters
    ----------
    pos : array
        Position of the particles, with units. When calculating, units are converted to physical kpc.
    vel : array
        Velocity of the particles in pysical km/s.
    mass : array
        Masses of particles, with units. When calculatig, they are converted to Msun.
    ids : array, optional
        Array of unique particle ids. If provided, the function returns masks for bound particles and bound particle ids.
    soft : array, optional
        Softening of particles. Not required, results do not differ a lot.
    cm : array, optional
        Initial Center of mass velocity estimation.
    vcm : array, optional
        Initial Center of mass velocity estimation.
    refine, bool, optional
        Whether to refine the undinding. Default is false.
    delta : float, optional
        Relative tolerance for determined if the unbinding is refined. Default is 1E-5.
    verbose : bool, optional
        Whether to print when running. Work in progrees. default is False.
    """

    cm = np.average(pos, axis=0, weights=mass) if cm is None else cm
    vcm = np.average(vel, axis=0, weights=mass) if vcm is None else vcm
    G = -unyt_quantity(4.300917270038e-06, "kpc/Msun * km**2/s**2").in_units(pos.units/mass.units * (vel.units)**2)
    
    for i in range(100):
        radii = np.sqrt( (pos[:,0]-cm[0])**2 +
                         (pos[:,1]-cm[1])**2 + 
                         (pos[:,2]-cm[2])**2
                       )
        abs_vel = np.sqrt( (vel[:,0]-vcm[0])**2 +
                         (vel[:,1]-vcm[1])**2 + 
                         (vel[:,2]-vcm[2])**2
                       )
    
        kin = 0.5 * mass * abs_vel**2
        pot = G * mass * mass.sum() / radii
        E = kin + pot
        bound_mask = E < 0
        
        
        N = int(np.rint(np.minimum(0.1 * np.count_nonzero(bound_mask), 32)))
        most_bound_ids = np.argsort(E)[:N]
        most_bound_mask = np.zeros(len(E), dtype=bool)
        most_bound_mask[most_bound_ids] = True
        
        new_cm = np.average(pos[most_bound_mask], axis=0, weights=mass[most_bound_mask])
        new_vcm = np.average(vel[most_bound_mask], axis=0, weights=mass[most_bound_mask])        
     
        delta_cm = np.sqrt(np.sum((new_cm - cm)**2, axis=0)) / np.linalg.norm(cm) < delta
        delta_vcm =  np.sqrt(np.sum((new_vcm - vcm)**2, axis=0)) / np.linalg.norm(vcm) < delta        
        
        if not refine or (delta_cm and delta_vcm):
            return E, kin, pot
            #return (bound_mask, most_bound_mask, ids[bound_mask], ids[most_bound_mask]) if ids is not None else (bound_mask, most_bound_mask)

        cm, vcm = copy(new_cm), copy(new_vcm)





