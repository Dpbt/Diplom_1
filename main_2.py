# from numpy import ndarray
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from ipywidgets import IntProgress
from numpy.lib.function_base import average
from tqdm import tqdm

from utils import (generate_random_profiles, generate_school_capacities, generate_k_restricted_preferences,
                   calculate_utility, calculate_utilities_from_prob)
from algorithm import k_boston_algorithm, k_gs_algorithm, manipulation_algorithm, algorithm_sampler


# Допилить отдельные полезности для манипуляторов / честных игроков, мб отдельную статистику по unassigned_students для них
def run_experiment_k(algorithm: str,
                   num_students: int,
                   num_schools: int,
                   profiles: np.ndarray,
                   capacities: np.ndarray,
                   num_repeat_sampler: int,
                   # num_repeat_for_k: int,
                   k: int,
                   epsilon: float,
                   num_manipulations: int
                   ):

    # На данный момент считается, что boston только для k = num_schools
    # Иначе, возможно, надо будет другую схему манипуляций для boston
    if algorithm == 'boston':
        k = num_schools

    if algorithm == 'boston':
        preferences = generate_k_restricted_preferences(profiles, k)
        manipulators = [0 for _ in range(num_students)]
    elif algorithm == 'gs':
        # Возможно, тут надо еще и это много раз повторять, если внутри manipulation_algorithm есть случайный выбор манипуляции/человека
        preferences, manipulators = manipulation_algorithm(algorithm=algorithm,
                                                           num_students=num_students,
                                                           num_schools=num_schools,
                                                           profiles=profiles,
                                                           capacities=capacities,
                                                           k=k,
                                                           epsilon=epsilon,
                                                           num_manipulations=num_manipulations)
    else:
        raise ValueError('Algorithm must be either "boston" or "gs"')

    probabilities, average_percentage_unassigned_students = algorithm_sampler(algorithm=algorithm,
                                                                              num_students=num_students,
                                                                              num_schools=num_schools,
                                                                              preferences=preferences,
                                                                              capacities=capacities,
                                                                              k=k,
                                                                              num_repeat=num_repeat_sampler)

    utilities = calculate_utilities_from_prob(num_students=num_students,
                                              num_schools=num_schools,
                                              probabilities=probabilities,
                                              profiles=profiles)

    return probabilities, utilities, manipulators, average_percentage_unassigned_students


# усреднение по профилям; среднее число манипуляторов
def run_experiment(num_students: int,
                   num_schools: int,
                   capacities: np.ndarray = None,
                   capacities_fixed: bool = False,
                   num_repeats_profiles: int = 10,
                   num_repeat_sampler: int = 1000,
                   epsilon: float = 0.1,
                   num_manipulations: int = 3  # 3?
                   ):

    if num_students < num_schools:
        raise ValueError("Number of students cannot be less than the number of schools.")

    experiment_results = pd.DataFrame(columns=["num_students", "num_schools", "capacities", "capacities_generated",
                                               "capacities_fixed", "num_repeats_profiles",
                                         "num_repeat_sampler", "epsilon", "num_manipulations",
                                         "algorithm", "k", "probabilities", "utilities", "average_utility",
                                         "average_number_manipulations",
                                         "average_percentage_manipulators", "average_percentage_unassigned_students"])

    sum_probabilities = np.zeros((num_schools + 1, num_students, num_schools + 1))
    sum_utilities = np.zeros((num_schools + 1, num_students))
    sum_number_manipulations = np.zeros(num_schools + 1)
    sum_number_manipulators = np.zeros(num_schools + 1)
    sum_percentage_unassigned_students = np.zeros(num_schools + 1)

    if capacities is not None:
        if np.sum(capacities) != num_students:
            raise ValueError("Capacities must sum to number of students.")
        capacities_flag = 0
    else:
        if capacities_fixed:
            capacities_flag = 1
        else:
            capacities_flag = 2
    # capacities_flag = True if capacities is None else False

    for profile_number in range(num_repeats_profiles):
        profiles = generate_random_profiles(num_students=num_students, num_schools=num_schools)

        if capacities_flag == 1 and profile_number == 0:
            capacities = generate_school_capacities(num_students=num_students, num_schools=num_schools)
        elif capacities_flag == 2:
            capacities = generate_school_capacities(num_students=num_students, num_schools=num_schools)
            
        # if capacities_fixed:
        #     if profile_number == 0:
        #         if capacities_flag:
        #             capacities = generate_school_capacities(num_students=num_students, num_schools=num_schools)
        #         else:
        #             if np.sum(capacities) != num_students:
        #                 raise ValueError("Capacities must sum to number of students.")
        # else:
        #     if capacities_flag:
        #         capacities = generate_school_capacities(num_students=num_students, num_schools=num_schools)
        #     else:
        #         if np.sum(capacities) != num_students:
        #             raise ValueError("Capacities must sum to number of students.")

        print(capacities_flag, capacities_flag, capacities)

        # Если доделать boston для k < num_schools, то добавить цикл для boston (и поменять ужас сколько индексов),
        # а внутри run_experiment_k переделать отработку boston
        # boston algorithm
        k_boston = num_schools
        probabilities, utilities, manipulators, average_percentage_unassigned_students = run_experiment_k(algorithm="boston",
                                                                 num_students=num_students,
                                                                 num_schools=num_schools,
                                                                 profiles=profiles,
                                                                 capacities=capacities,
                                                                 num_repeat_sampler=num_repeat_sampler,
                                                                 k=k_boston,
                                                                 epsilon=epsilon,
                                                                 num_manipulations=num_manipulations)

        sum_probabilities[0] += probabilities
        sum_utilities[0] += utilities
        sum_number_manipulations[0] += np.sum(manipulators)
        sum_number_manipulators[0] += np.count_nonzero(manipulators)
        sum_percentage_unassigned_students[0] += average_percentage_unassigned_students

        # gs algorithm
        for k_gs in range(1, num_schools + 1):
            probabilities, utilities, manipulators, average_percentage_unassigned_students = run_experiment_k(algorithm="gs",
                                                                     num_students=num_students,
                                                                     num_schools=num_schools,
                                                                     profiles=profiles,
                                                                     capacities=capacities,
                                                                     num_repeat_sampler=num_repeat_sampler,
                                                                     k=k_gs,
                                                                     epsilon=epsilon,
                                                                     num_manipulations=num_manipulations)

            sum_probabilities[k_gs] += probabilities
            sum_utilities[k_gs] += utilities
            sum_number_manipulations[k_gs] += np.sum(manipulators)
            sum_number_manipulators[k_gs] += np.count_nonzero(manipulators)
            sum_percentage_unassigned_students[k_gs] += average_percentage_unassigned_students

    average_probabilities = sum_probabilities / num_repeats_profiles
    average_utilities = sum_utilities / num_repeats_profiles
    average_utility = np.sum(average_utilities, axis=1) / num_students
    average_number_manipulations = sum_number_manipulations / num_repeats_profiles
    average_percentage_manipulators = (sum_number_manipulators / num_repeats_profiles) / num_students * 100
    average_percentage_unassigned_students = sum_percentage_unassigned_students / num_repeats_profiles

    new_row_boston = {"num_students": num_students,
                       "num_schools": num_schools,
                       "capacities": capacities,
                       "capacities_generated": False if capacities_flag == 0 else True,
                       "capacities_fixed": capacities_fixed,
                       "num_repeats_profiles": num_repeats_profiles,
                       "num_repeat_sampler": num_repeat_sampler,
                       "epsilon": epsilon,
                       "num_manipulations": num_manipulations,
                       "algorithm": "boston",
                       "k": k_boston,
                       "probabilities": average_probabilities[0],
                       "utilities": average_utilities[0],
                       "average_utility": average_utility[0],
                       "average_number_manipulations": average_number_manipulations[0],
                       "average_percentage_manipulators": average_percentage_manipulators[0],
                       "average_percentage_unassigned_students": average_percentage_unassigned_students[0]
                      }

    experiment_results = pd.concat([experiment_results, pd.DataFrame([new_row_boston])], ignore_index=True)

    for exp_num in range(1, num_schools + 1):
        new_row_gs = {"num_students": num_students,
                       "num_schools": num_schools,
                       "capacities": capacities,
                       "capacities_generated": False if capacities_flag == 0 else True,
                       "capacities_fixed": capacities_fixed,
                       "num_repeats_profiles": num_repeats_profiles,
                       "num_repeat_sampler": num_repeat_sampler,
                       "epsilon": epsilon,
                       "num_manipulations": num_manipulations,
                       "algorithm": "gs",
                       "k": exp_num,
                       "probabilities": average_probabilities[exp_num],
                       "utilities": average_utilities[exp_num],
                       "average_utility": average_utility[exp_num],
                       "average_number_manipulations": average_number_manipulations[exp_num],
                       "average_percentage_manipulators": average_percentage_manipulators[exp_num],
                       "average_percentage_unassigned_students": average_percentage_unassigned_students[exp_num]
                      }

        experiment_results = pd.concat([experiment_results, pd.DataFrame([new_row_gs])], ignore_index=True)


    return experiment_results


def massive_run(tests: list, display_progress: bool = False):
    # Принимает список экспериментов, запускает их параллельно, формирует pd.df
    exp_num = 0

    test_results = pd.DataFrame(columns=["num_students", "num_schools", "capacities", "capacities_generated",
                                         "capacities_fixed", "num_repeats_profiles",
                                         "num_repeat_sampler", "epsilon", "num_manipulations",
                                         "algorithm", "k", "probabilities", "utilities", "average_utility",
                                         "average_percentage_manipulators", "average_percentage_unassigned_students"])

    if display_progress:
        iterator = tqdm(tests, desc="Выполнение тестов")
    else:
        iterator = tests

    for test in iterator:
        exp_num += 1

        params = {
            'num_students': test['num_students'],
            'num_schools': test['num_schools']
        }

        if 'capacities' in test:
            params['capacities'] = test['capacities']
            params['capacities_fixed'] = True
        else:
            if 'capacities_fixed' in test:
                params['capacities_fixed'] = test['capacities_fixed']


        for key in ['num_repeats_profiles', 'num_repeat_sampler', 'epsilon', 'num_manipulations']:
            if key in test:
                params[key] = test[key]

        experiment_results = run_experiment(**params)

        test_results = pd.concat([test_results, experiment_results], ignore_index=True)

    return test_results



def parallel_run(tests: list, batch_size: int = 1, n_jobs: int = 1, display_progress: bool = False):

    num_batch = int(len(tests)/batch_size) if len(tests) % batch_size == 0 else int(len(tests)/batch_size) + 1
    tests_with_batch = [tests[i * batch_size : (i + 1) * batch_size] for i in range(num_batch)]

    with Parallel(n_jobs=n_jobs, verbose=10, backend='threading') as parallel:
        results = parallel(delayed(massive_run)(test_batch, display_progress=display_progress) for test_batch in tests_with_batch)

    test_results = pd.concat(results, ignore_index=True)

    return test_results

# test = [num_students, num_schools, capacities, num_repeats_profiles, num_repeat_sampler, epsilon, num_manipulations]


if __name__ == '__main__':
    # assignments, unassigned_students, utilities = run_experiment(algorithm='boston',
    #                                                              num_students=10,
    #                                                              num_schools=4,
    #                                                              num_repeat=100,
    #                                                              epsilon=0.1,
    #                                                              num_manipulations=0)

    # print(assignments)
    # print(unassigned_students)
    # print(utilities)
    # print(preferences)

    num_students = 20
    num_schools = 8
    profiles = generate_random_profiles(num_students=num_students, num_schools=num_schools)
    capacities = generate_school_capacities(num_students=num_students, num_schools=num_schools)
    num_repeat_sampler = 100
    k = 2
    epsilon = 0.1
    num_manipulations = 5

    # probabilities, utilities, manipulators, average_percentage_unassigned_students = run_experiment_k(algorithm='gs',
    #                                                                                                 num_students=num_students,
    #                                                                                                 num_schools=num_schools,
    #                                                                                                 profiles=profiles,
    #                                                                                                 capacities=capacities,
    #                                                                                                 num_repeat_sampler=num_repeat_sampler,
    #                                                                                                 k=k,
    #                                                                                                 epsilon=epsilon,
    #                                                                                                 num_manipulations=num_manipulations
    #                                                                                                 )
    #
    # print(probabilities)
    # print(utilities)
    # print(manipulators)
    # print(average_percentage_unassigned_students)

    pd.set_option('display.max_columns', None)

    experiment_results = run_experiment(num_students=num_students,
                                        num_schools=num_schools,
                                        num_repeats_profiles=5,
                                        num_repeat_sampler=num_repeat_sampler,
                                        epsilon=epsilon,
                                        num_manipulations=num_manipulations)

    print(experiment_results)

    experiment_results.to_csv('experiment_results.csv', index=False)
