"""
Note: Moved to umpyre (pip install umpyre)

Get stats about packages. Your own, or other's.
Things like...

# >>> import collections
# >>> modules_info_df(collections)
#                       lines  empty_lines  ...  num_of_functions  num_of_classes
# collections.__init__   1273          189  ...                 1               9
# collections.abc           3            1  ...                 0              25
# <BLANKLINE>
# [2 rows x 7 columns]
# >>> modules_info_df_stats(collections.abc)
# lines                      1276.000000
# empty_lines                 190.000000
# comment_lines                73.000000
# docs_lines                  133.000000
# function_lines              138.000000
# num_of_functions              1.000000
# num_of_classes               34.000000
# empty_lines_ratio             0.148903
# comment_lines_ratio           0.057210
# function_lines_ratio          0.108150
# mean_lines_per_function     138.000000
# dtype: float64
# >>> stats_of(['urllib', 'json', 'collections'])
#                               urllib         json  collections
# empty_lines_ratio           0.157034     0.136818     0.148903
# comment_lines_ratio         0.074142     0.038432     0.057210
# function_lines_ratio        0.213907     0.449654     0.108150
# mean_lines_per_function    13.463768    41.785714   138.000000
# lines                    4343.000000  1301.000000  1276.000000
# empty_lines               682.000000   178.000000   190.000000
# comment_lines             322.000000    50.000000    73.000000
# docs_lines                425.000000   218.000000   133.000000
# function_lines            929.000000   585.000000   138.000000
# num_of_functions           69.000000    14.000000     1.000000
# num_of_classes             55.000000     3.000000    34.000000
"""
