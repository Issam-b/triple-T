# command codenames between sever and client
commands = {
    'move': { 'cmd': 'm', 'len': '2'},
    'quit': 'q',
    'echo': { 'cmd': 'e', 'len': '2'},
    'confirm': { 'cmd': 'c', 'len': '2'},
    'confirm_states': {
        'id_received': '1',
        'game_info_received': '2',
    },
    'lose': { 'cmd': 'l', 'len': '1'},
    'win': { 'cmd': 'w', 'len': '1'},
    'draw': { 'cmd': 'd', 'len': '1'},
    'your_turn': { 'cmd': 'u', 'len': '1'},
    'other_turn': { 'cmd': 'o', 'len': '1'},
    'game_info': { 'cmd': 'g', 'len': '6'}
}